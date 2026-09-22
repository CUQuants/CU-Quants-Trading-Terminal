import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.grouping import group_articles
from news.claude import ClaudeUnavailableError
from news.models import Article, Insight
from news.service import NewsEventProcessor
from routes.news_events import router


BASE_TIME = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


def article(article_id: str, title: str, minutes: int = 0) -> Article:
    published_at = BASE_TIME + timedelta(minutes=minutes)
    return Article(
        id=article_id,
        canonical_url=f"https://news.test/{article_id}",
        source="Test Wire",
        title=title,
        excerpt="A short excerpt.",
        published_at_utc=published_at,
        ingested_at_utc=published_at,
        category="Crypto",
        assets=["BTC"],
        matched_pairs=["BTC/USD"],
    )


class FakeClaude:
    model = "claude-test"

    def __init__(self):
        self.calls = 0

    async def create_insight(self, event):
        self.calls += 1
        return Insight(
            event_id=event.id,
            model_version=self.model,
            status="ready",
            factual_summary="A factual summary.",
            market_context="Possible market context.",
            affected_assets=["BTC"],
            what_to_watch=["Venue status"],
            time_horizon="immediate",
            impact_level="medium",
            confidence="medium",
            evidence_article_ids=[event.representative_article_id],
            prompt_version="news-insight-v1",
            schema_version="1",
        )

    async def aclose(self):
        pass


class FailingClaude(FakeClaude):
    async def create_insight(self, event):
        self.calls += 1
        raise ClaudeUnavailableError("temporary failure")


@pytest.mark.asyncio
async def test_caches_unchanged_events_and_refreshes_changed_events():
    claude = FakeClaude()
    processor = NewsEventProcessor(claude)
    first = article("a1", "Exchange suspends Bitcoin withdrawals after outage")

    await processor.process([first])
    await processor.process([first])
    assert claude.calls == 1

    second = article(
        "a2",
        "Exchange suspends Bitcoin withdrawals following outage",
        minutes=10,
    )
    events = await processor.process([first, second])

    assert claude.calls == 2
    assert len(events[0].related_article_ids) == 2


@pytest.mark.asyncio
async def test_unconfigured_claude_does_not_break_event_feed():
    processor = NewsEventProcessor()

    events = await processor.process([
        article("a1", "Exchange suspends Bitcoin withdrawals after outage")
    ])

    assert events[0].insight.status == "unavailable"


@pytest.mark.asyncio
async def test_claude_failure_does_not_break_event_feed():
    processor = NewsEventProcessor(FailingClaude())

    events = await processor.process([
        article("a1", "Exchange suspends Bitcoin withdrawals after outage")
    ])

    assert events[0].insight.status == "unavailable"


def test_events_route_filters_by_pair_and_limits_results():
    processor = NewsEventProcessor()
    processor._events = group_articles([
        article("a1", "Exchange suspends Bitcoin withdrawals after outage")
    ])

    app = FastAPI()
    app.include_router(router)
    app.state.news_event_processor = processor
    client = TestClient(app)

    response = client.get("/news/events", params={"pair": "BTC/USD", "limit": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["related_article_ids"] == ["a1"]
    assert "content_hash" not in response.json()[0]


def test_events_route_returns_503_without_processor():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/news/events")

    assert response.status_code == 503
