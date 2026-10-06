"""HTTP contracts for cached news and provider status; no live provider calls."""

import os
import sys
import threading
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.providers import NewsProvider, ProviderResult
from news.normalization import normalize_article
import news.service as news_service
import routes.news as news_routes
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
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["headline"] == "Bitcoin mining update"
    assert data["items"][0]["category"] == "Crypto"
    assert set(data["items"][0]) == {
        "id", "sourceId", "sourceName", "url", "headline", "publishedAt",
        "excerpt", "category", "matchedAssets", "matchedPairs",
    }
    assert data["items"][0]["publishedAt"].startswith("2026-01-03T00:00:00")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_news_cache_read_runs_in_a_worker_thread(news_client, monkeypatch):
    client, service, _ = news_client
    get_article_page = service.get_article_page
    threads = []

    def read_cache(**kwargs):
        threads.append(threading.get_ident())
        return get_article_page(**kwargs)

    monkeypatch.setattr(service, "get_article_page", read_cache)
    response = await client.get("/news")
    assert response.status_code == 200
    assert len(threads) == 1
    assert threads[0] != threading.get_ident()


@pytest.mark.asyncio
async def test_status_reports_refresh_metadata_and_provider_health(news_client):
    client, service, calls = news_client
    response = await client.get("/news/status")
    assert response.status_code == 200
    data = response.json()
    assert data["checkedAt"] is not None
    assert data["sources"][0]["id"] == "example"
    assert data["sources"][0]["status"] == "healthy"
    assert data["sources"][0]["lastSuccessfulRefreshAt"] is not None
    assert "message" not in data["sources"][0]
    assert data["ai"]["status"] == "unavailable"
    assert {option["id"] for option in data["categories"]} == {
        "Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics",
    }
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_news_omits_empty_excerpt_and_retains_refresh_timestamp(news_client):
    client, service, _ = news_client
    service._cache[0].summary = ""
    response = await client.get("/news")
    data = response.json()
    assert response.status_code == 200
    assert "excerpt" not in data["items"][0]
    assert data["lastSuccessfulRefreshAt"] is not None


def test_news_preserves_null_refresh_timestamp_before_collection():
    app = FastAPI()
    app.include_router(router)
    app.state.news_service = NewsService([])
    with TestClient(app) as client:
        response = client.get("/news")
    assert response.status_code == 200
    assert response.json() == {
        "items": [], "total": 0,
        "lastSuccessfulRefreshAt": None, "staleAfterSeconds": 600,
    }


@pytest.mark.asyncio
async def test_news_frontend_pair_and_timeframe_parameters(news_client):
    client, service, calls = news_client
    response = await client.get("/news", params=[
        ("pair", "BTC/USD"), ("pair", "ETH/USD"),
    ])
    assert response.status_code == 200
    assert [item["matchedPairs"] for item in response.json()["items"]] == [
        ["BTC/USD"], ["ETH/USD"],
    ]
    response = await client.get("/news", params={"timeframe": "1h"})
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_news_accepts_repeated_pair_and_asset_filters(news_client):
    client, service, calls = news_client
    response = await client.get("/news", params=[
        ("pairs", "BTC/USD"), ("pairs", "ETH/USD"), ("matched_only", "true"),
    ])
    assert response.status_code == 200
    assert {item["headline"] for item in response.json()["items"]} == {
        "Bitcoin mining update", "Ethereum staking update",
    }
    assert all(item["matchedPairs"] for item in response.json()["items"])

    response = await client.get("/news", params=[
        ("assets", "BTC"), ("assets", "ETH"), ("matched_only", "true"),
    ])
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert not any(item.matched for item in service.get_articles())


@pytest.mark.asyncio
async def test_news_combines_category_source_and_query_filters(news_client):
    client, service, calls = news_client
    response = await client.get("/news", params={
        "category": "Crypto", "source": "Messari", "q": "STAKING",
        "limit": 1, "offset": 0,
    })
    assert response.status_code == 200
    assert [item["headline"] for item in response.json()["items"]] == ["Ethereum staking update"]

    response = await client.get("/news", params={"category": "All", "limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [item["headline"] for item in response.json()["items"]] == ["Ethereum staking update"]


@pytest.mark.asyncio
@pytest.mark.parametrize(("params", "total", "indices"), [
    ({"pair": "BTC/USD", "limit": 10, "offset": 20}, 498, list(range(20, 30))),
    ({"pair": "BTC/USD", "limit": 10, "offset": 600}, 498, []),
    ({"pair": "BTC/USD", "matched_only": True, "limit": 10, "offset": 20},
     249, list(range(40, 60, 2))),
    ({"matched_only": True, "limit": 10}, 0, []),
    ({"source": "Marketaux", "category": "Trad-Fi", "q": "Ethereum",
      "timeframe": "1h", "limit": 4, "offset": 3}, 30, [7, 9, 11, 13]),
])
async def test_news_matches_and_projects_only_requested_page(
    news_client, monkeypatch, params, total, indices,
):
    client, service, provider_calls = news_client
    now = datetime.now(timezone.utc)
    records = [
        {"source": "Finnhub", "title": "Bitcoin missing date",
         "url": "https://example.test/undated"},
        {"source": "Finnhub", "title": "Bitcoin invalid URL",
         "url": "ftp://example.test/invalid", "published_at": now},
    ]
    records.extend({
        "source": "Finnhub" if index % 2 == 0 else "Marketaux",
        "title": f"{'Bitcoin' if index % 2 == 0 else 'Ethereum'} report {index}",
        "category": "Crypto" if index % 2 == 0 else "Trad-Fi",
        "url": f"https://example.test/{index}",
        "published_at": now - timedelta(minutes=index + 0.5),
    } for index in range(498))
    service._cache = [normalize_article(record) for record in records]
    before = [article.model_dump() for article in service._cache]
    match_article = news_service.match_article
    project_article = news_routes._to_api_article
    matched_titles = []
    projected_titles = []

    def counted_match(article, *args):
        matched_titles.append(article.title)
        return match_article(article, *args)

    def counted_projection(service, article):
        projected_titles.append(article.title)
        return project_article(service, article)

    monkeypatch.setattr(news_service, "match_article", counted_match)
    monkeypatch.setattr(news_routes, "_to_api_article", counted_projection)
    response = await client.get("/news", params=params)
    expected = [records[index + 2]["title"] for index in indices]
    assert response.status_code == 200
    assert response.json()["total"] == total
    assert [item["headline"] for item in response.json()["items"]] == expected
    assert matched_titles == expected
    assert projected_titles == expected
    assert [article.model_dump() for article in service._cache] == before
    assert len(provider_calls) == 1


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
