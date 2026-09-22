import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.grouping import group_articles
from news.models import Article


BASE_TIME = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


def article(
    article_id: str,
    title: str,
    *,
    url: str | None = None,
    assets: list[str] | None = None,
    published_at: datetime = BASE_TIME,
) -> Article:
    return Article(
        id=article_id,
        canonical_url=url or f"https://news.test/{article_id}",
        source="Test Wire",
        title=title,
        excerpt="Short source excerpt.",
        published_at_utc=published_at,
        ingested_at_utc=published_at,
        category="Crypto",
        assets=assets or [],
        matched_pairs=[f"{assets[0]}/USD"] if assets else [],
    )


def test_groups_reports_of_the_same_event_after_url_deduplication():
    articles = [
        article("a1", "Exchange suspends Bitcoin withdrawals after outage", assets=["BTC"]),
        article(
            "a2",
            "Exchange suspends Bitcoin withdrawals following outage",
            assets=["BTC"],
            published_at=BASE_TIME + timedelta(minutes=20),
        ),
        article(
            "duplicate",
            "Duplicate copy",
            url="https://news.test/a1/",
            assets=["BTC"],
            published_at=BASE_TIME - timedelta(minutes=1),
        ),
    ]

    events = group_articles(articles)

    assert len(events) == 1
    assert set(events[0].related_article_ids) == {"a1", "a2"}
    assert events[0].assets == ["BTC"]


def test_does_not_group_similar_headlines_about_different_assets():
    events = group_articles([
        article("btc", "Bitcoin ETF inflows rise after Fed decision", assets=["BTC"]),
        article("eth", "Ethereum ETF inflows rise after Fed decision", assets=["ETH"]),
    ])

    assert len(events) == 2


def test_does_not_group_old_reports():
    events = group_articles([
        article("old", "Exchange suspends Bitcoin withdrawals after outage", assets=["BTC"]),
        article(
            "new",
            "Exchange suspends Bitcoin withdrawals after outage",
            assets=["BTC"],
            published_at=BASE_TIME + timedelta(hours=13),
        ),
    ])

    assert len(events) == 2
