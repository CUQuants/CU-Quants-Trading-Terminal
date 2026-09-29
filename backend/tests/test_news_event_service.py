import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import NewsArticle
from news.claude import ClaudeUnavailableError
from news.models import Insight, InsightStatement
from news.processor import NewsEventProcessor


BASE_TIME = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def article(url: str, title: str, minutes: int = 0) -> NewsArticle:
    return NewsArticle(
        source="Test Wire",
        title=title,
        summary="A short excerpt.",
        url=url,
        published_at=BASE_TIME + timedelta(minutes=minutes),
        category="Crypto",
        assets=["BTC"],
    )


class FakeClaude:
    model = "claude-test"

    def __init__(self):
        self.calls = 0

    async def create_insight(self, event):
        self.calls += 1
        citation = [event.articles[0].id]
        return Insight(
            event_id=event.id,
            generated_at=BASE_TIME,
            model=self.model,
            factual_summary=[InsightStatement(text="A factual summary.", article_ids=citation)],
            market_context=[InsightStatement(text="Possible context.", article_ids=citation)],
            what_to_watch=[InsightStatement(text="Watch venue status.", article_ids=citation)],
            confidence="medium",
            prompt_version="news-insight-v2",
            schema_version="2",
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
    first = article(
        "https://news.test/one",
        "Exchange suspends Bitcoin withdrawals after outage",
    )

    await processor.process([first])
    await processor.process([first])
    assert claude.calls == 1

    second = article(
        "https://news.test/two",
        "Exchange suspends Bitcoin withdrawals following outage",
        minutes=10,
    )
    events = await processor.process([first, second])

    assert claude.calls == 2
    assert len(events[0].articles) == 2
    assert events[0].insight_status == "validated"


@pytest.mark.asyncio
async def test_unconfigured_claude_does_not_break_event_feed():
    processor = NewsEventProcessor()

    events = await processor.process([article(
        "https://news.test/one",
        "Exchange suspends Bitcoin withdrawals after outage",
    )])

    assert events[0].insight_status == "unavailable"
    assert events[0].insight is None


@pytest.mark.asyncio
async def test_claude_failure_does_not_break_event_feed():
    processor = NewsEventProcessor(FailingClaude())

    events = await processor.process([article(
        "https://news.test/one",
        "Exchange suspends Bitcoin withdrawals after outage",
    )])

    assert events[0].insight_status == "unavailable"
    assert events[0].insight is None
