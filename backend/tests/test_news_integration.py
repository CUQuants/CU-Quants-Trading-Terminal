"""Provider-to-API integration test with a mocked Claude boundary."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.claude import ClaudeClient
from news.processor import NewsEventProcessor
from news.providers import NewsProvider, ProviderResult
from news.service import NewsService
from routes.news import router


@pytest.mark.asyncio
async def test_provider_refresh_groups_and_enriches_event_for_frontend():
    now = datetime.now(timezone.utc)
    provider_calls = 0
    claude_calls = 0

    async def fetch():
        nonlocal provider_calls
        provider_calls += 1
        if provider_calls > 1:
            return ProviderResult([], ["temporary_failure"])
        return ProviderResult([
            {
                "source": "Wire One",
                "title": "Exchange suspends Bitcoin withdrawals after outage",
                "summary": "The exchange reported an infrastructure outage.",
                "url": "https://news.test/one",
                "published_at": now,
                "category": "Crypto",
                "assets": ["BTC"],
            },
            {
                "source": "Wire Two",
                "title": "Exchange suspends Bitcoin withdrawals following outage",
                "summary": "Withdrawals are temporarily unavailable.",
                "url": "https://news.test/two",
                "published_at": now + timedelta(minutes=5),
                "category": "Crypto",
                "assets": ["BTC"],
            },
        ])

    async def claude_handler(request: httpx.Request):
        nonlocal claude_calls
        claude_calls += 1
        prompt = json.loads(json.loads(request.content)["messages"][0]["content"])
        ids = [article["id"] for article in prompt["articles"]]
        statement = lambda text: {"text": text, "article_ids": ids}
        return httpx.Response(200, json={
            "model": "claude-test",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 120, "output_tokens": 60},
            "content": [{"type": "text", "text": json.dumps({
                "status": "ready",
                "affected_assets": ["BTC"],
                "factual_summary": [statement("Two reports describe a withdrawal outage.")],
                "market_context": [statement("Venue liquidity may be temporarily affected.")],
                "what_to_watch": [statement("Watch withdrawal status and venue spreads.")],
                "confidence": "high",
            })}],
        })

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(claude_handler))
    processor = NewsEventProcessor(
        ClaudeClient("key", "claude-test", client=http_client)
    )
    service = NewsService(
        [NewsProvider("Test Provider", fetch)],
        on_refresh=processor.process,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.news_service = service
    app.state.news_event_processor = processor

    try:
        await service.refresh()
        assert processor.events[0].insight_status == "pending"
        await processor._task
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/news/events",
                params={"timeframe": "24h", "pair": "BTC/USD"},
            )
            assert response.status_code == 200
            event = response.json()["items"][0]
            assert event["sourceCount"] == 2
            assert len(event["articles"]) == 2
            assert event["insightStatus"] == "validated"
            cited = event["insight"]["factualSummary"][0]["articleIds"]
            assert set(cited) == {article["id"] for article in event["articles"]}

            await service.refresh()
            response = await client.get("/news/events", params={"timeframe": "24h"})
            assert response.status_code == 200
            assert response.json()["total"] == 1
            status = await client.get("/news/status")
            assert status.json()["sources"][0]["status"] == "unavailable"
        assert claude_calls == 1
    finally:
        await service.aclose()
        await processor.aclose()
        await http_client.aclose()
