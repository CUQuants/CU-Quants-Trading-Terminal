"""HTTP contracts for cached news and provider status; no live provider calls."""

import os
import sys
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.providers import NewsProvider, ProviderResult
from news.service import NewsService
from routes.news import router


@pytest_asyncio.fixture
async def news_client():
    calls = []

    async def fetch():
        calls.append(True)
        return ProviderResult([
            {
                "source": "CoinDesk", "title": "Bitcoin mining update",
                "summary": "Bitcoin miners announce expansion",
                "url": "https://example.test/btc", "category": "Crypto",
                "published_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
            },
            {
                "source": "Messari", "title": "Ethereum staking update",
                "summary": "Ethereum staking adoption increases",
                "url": "https://example.test/eth", "category": "Crypto",
                "published_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            },
            {
                "source": "Reuters", "title": "Company earnings report",
                "summary": "Quarterly earnings exceed expectations",
                "url": "https://example.test/equity", "category": "Trad-Fi",
                "published_at": None,
            },
        ])

    service = NewsService([NewsProvider("Example", fetch)])
    app = FastAPI()
    app.include_router(router)
    app.state.news_service = service
    await service.refresh()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as client:
            yield client, service, calls
    finally:
        await service.aclose()


@pytest.mark.parametrize("path", ["/news", "/news/status"])
def test_news_routes_return_503_when_service_is_missing(path):
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_news_returns_serializable_cached_articles_without_refetching(news_client):
    client, service, calls = news_client
    response = await client.get("/news")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["title"] == "Bitcoin mining update"
    assert data[0]["category"] == "Crypto"
    assert set(data[0]) == {
        "source", "title", "summary", "url", "published_at", "category",
        "assets", "matched", "match_terms",
    }
    assert data[0]["published_at"].startswith("2026-01-03T00:00:00")
    assert data[2]["published_at"] is None
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_status_reports_refresh_metadata_and_provider_health(news_client):
    client, service, calls = news_client
    response = await client.get("/news/status")
    assert response.status_code == 200
    data = response.json()
    assert data["article_count"] == 3
    assert data["refresh_interval_seconds"] == 300
    assert data["refreshing"] is False
    assert data["last_refresh"] is not None
    assert data["last_success"] is not None
    assert data["providers"][0]["name"] == "Example"
    assert data["providers"][0]["state"] == "ok"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_news_accepts_repeated_pair_and_asset_filters(news_client):
    client, service, calls = news_client
    response = await client.get("/news", params=[
        ("pairs", "BTC/USD"), ("pairs", "ETH/USD"), ("matched_only", "true"),
    ])
    assert response.status_code == 200
    assert {item["title"] for item in response.json()} == {
        "Bitcoin mining update", "Ethereum staking update",
    }
    assert all(item["matched"] for item in response.json())

    response = await client.get("/news", params=[
        ("assets", "BTC"), ("assets", "ETH"), ("matched_only", "true"),
    ])
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert not any(item.matched for item in service.get_articles())


@pytest.mark.asyncio
async def test_news_combines_category_source_and_query_filters(news_client):
    client, service, calls = news_client
    response = await client.get("/news", params={
        "category": "Crypto", "source": "Messari", "q": "STAKING",
        "limit": 1, "offset": 0,
    })
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Ethereum staking update"]

    response = await client.get("/news", params={"category": "All", "limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Ethereum staking update"]


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 501}, {"offset": -1},
    {"category": "Unknown"}, {"matched_only": "not-a-boolean"},
])
async def test_news_rejects_invalid_query_parameters(news_client, params):
    client, service, calls = news_client
    response = await client.get("/news", params=params)
    assert response.status_code == 422
    assert len(calls) == 1
