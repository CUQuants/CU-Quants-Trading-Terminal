import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import NewsArticle
from news.grouping import apply_pairs, group_articles


BASE_TIME = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def article(
    title: str,
    url: str,
    *,
    assets: list[str],
    published_at: datetime = BASE_TIME,
) -> NewsArticle:
    return NewsArticle(
        source="Test Wire",
        title=title,
        summary="Short source excerpt.",
        url=url,
        published_at=published_at,
        category="Crypto",
        assets=assets,
    )


def test_groups_same_event_and_removes_exact_url_duplicates():
    events = group_articles([
        article(
            "Exchange suspends Bitcoin withdrawals after outage",
            "https://news.test/one",
            assets=["BTC"],
        ),
        article(
            "Exchange suspends Bitcoin withdrawals following outage",
            "https://news.test/two",
            assets=["BTC"],
            published_at=BASE_TIME + timedelta(minutes=20),
        ),
        article("Duplicate copy", "https://news.test/one", assets=["BTC"]),
    ])

    assert len(events) == 1
    assert len(events[0].articles) == 2
    assert events[0].matched_assets == ["BTC"]
    assert events[0].source_count == 1


def test_keeps_similar_headlines_about_different_assets_separate():
    events = group_articles([
        article(
            "Bitcoin ETF inflows rise after Fed decision",
            "https://news.test/btc",
            assets=["BTC"],
        ),
        article(
            "Ethereum ETF inflows rise after Fed decision",
            "https://news.test/eth",
            assets=["ETH"],
        ),
    ])

    assert len(events) == 2


def test_keeps_reports_more_than_twelve_hours_apart_separate():
    events = group_articles([
        article(
            "Exchange suspends Bitcoin withdrawals after outage",
            "https://news.test/old",
            assets=["BTC"],
        ),
        article(
            "Exchange suspends Bitcoin withdrawals after outage",
            "https://news.test/new",
            assets=["BTC"],
            published_at=BASE_TIME + timedelta(hours=13),
        ),
    ])

    assert len(events) == 2


def test_pair_matching_uses_base_asset_and_does_not_match_quote_only():
    event = group_articles([
        article("Bitcoin update", "https://news.test/btc", assets=["BTC", "USD"])
    ])[0]

    matched = apply_pairs(event, ["BTC/USD", "ETH/USD"])

    assert matched.matched_pairs == ["BTC/USD"]
