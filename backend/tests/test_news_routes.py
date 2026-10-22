"""News HTTP contracts using cached data and no live provider calls."""

import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.processor import NewsEventProcessor
from news.providers import NewsProvider, ProviderResult
from news.service import NewsService
from routes.news import router


@pytest_asyncio.fixture
async def news_client():
    calls = []
    now = datetime.now(timezone.utc)

    async def fetch():
        calls.append(True)
        return ProviderResult([
            {
                "source": "CoinDesk",
                "title": "Bitcoin mining update",
                "summary": "Bitcoin miners announce expansion",
                "url": "https://example.test/btc",
                "category": "Crypto",
                "published_at": now - timedelta(minutes=10),
            },
            {
                "source": "Messari",
                "title": "Ethereum staking update",
                "summary": "Ethereum staking adoption increases",
                "url": "https://example.test/eth",
                "category": "Crypto",
                "published_at": now - timedelta(hours=2),
            },
            {
                "source": "Reuters",
                "title": "Company earnings report",
                "summary": "Quarterly earnings exceed expectations",
                "url": "https://example.test/equity",
                "category": "Trad-Fi",
                "published_at": now - timedelta(days=2),
            },
        ])

    processor = NewsEventProcessor()
    service = NewsService(
        [NewsProvider("Example", fetch)],
        on_refresh=processor.process,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.news_service = service
    app.state.news_event_processor = processor
    await service.refresh()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client, calls
    finally:
        await service.aclose()


@pytest.mark.parametrize("path", ["/news", "/news/events", "/news/status"])
def test_news_routes_return_503_when_service_is_missing(path):
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_article_feed_matches_frontend_contract_without_refetching(news_client):
    client, calls = news_client

    response = await client.get("/news", params={"timeframe": "24h"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["headline"] == "Bitcoin mining update"
    assert data["lastSuccessfulRefreshAt"] is not None
    assert data["staleAfterSeconds"] == 600
    assert set(data["items"][0]) == {
        "id", "sourceId", "sourceName", "url", "headline", "publishedAt",
        "excerpt", "category", "matchedAssets", "matchedPairs",
    }
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_article_feed_filters_category_source_timeframe_and_pairs(news_client):
    client, calls = news_client

    response = await client.get("/news", params=[
        ("category", "Crypto"),
        ("source", "coindesk"),
        ("timeframe", "1h"),
        ("pair", "BTC/USD"),
        ("pair", "ETH/USD"),
    ])

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["matchedPairs"] == ["BTC/USD"]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_event_feed_contains_articles_and_safe_unavailable_insight(news_client):
    client, _ = news_client

    response = await client.get(
        "/news/events",
        params=[("timeframe", "24h"), ("pair", "BTC/USD")],
    )

    assert response.status_code == 200
    event = response.json()["items"][0]
    assert event["matchedPairs"] == ["BTC/USD"]
    assert event["sourceCount"] == 1
    assert event["insightStatus"] == "unavailable"
    assert event["insight"] is None
    assert "contentHash" not in event


@pytest.mark.asyncio
async def test_status_matches_frontend_contract(news_client):
    client, _ = news_client

    response = await client.get("/news/status")

    assert response.status_code == 200
    data = response.json()
    assert data["sources"][0]["id"] == "example"
    assert data["sources"][0]["status"] == "healthy"
    assert data["ai"]["status"] == "unavailable"
    assert {item["id"] for item in data["categories"]} == {
        "Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [
    {"limit": 0},
    {"limit": 101},
    {"timeframe": "30d"},
    {"category": "Sports"},
])
async def test_news_rejects_invalid_query_parameters(news_client, params):
    client, calls = news_client
    response = await client.get("/news", params=params)
    assert response.status_code == 422
    assert len(calls) == 1
