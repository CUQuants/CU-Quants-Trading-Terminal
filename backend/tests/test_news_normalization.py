"""News normalization, category precedence, matching, and exact-URL deduplication."""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.normalization import deduplicate_articles, match_article, normalize_article


def make_article(**overrides):
    return normalize_article({"source": "NewsAPI/Reuters", "title": "Market update", **overrides})


@pytest.mark.parametrize("raw", [None, [], {}, {"title": None}, {"title": 123},
                                  {"title": " \t"}, {"title": "<p></p>"}])
def test_missing_or_invalid_title_is_discarded(raw):
    assert normalize_article(raw) is None


def test_html_entities_and_script_contents_are_removed():
    article = make_article(
        title=" <b>Bitcoin</b> &amp; Ethereum&nbsp;rise ",
        summary="<p>First</p><p>Second<br>line</p><!-- hidden -->"
                "<script>alert('bad')</script><style>body { color: red }</style>",
    )

    assert article.title == "Bitcoin & Ethereum rise"
    assert article.summary == "First Second line"
    assert article.assets == ["BTC", "ETH"]


def test_unknown_html_declaration_does_not_discard_an_otherwise_valid_article():
    article = make_article(summary="<![unknown[hidden]]>Headline")

    assert article.title == "Market update"
    # HTMLParser rejects this declaration on older supported Python versions.
    assert article.summary in ("", "Headline")


def test_invalid_optional_fields_are_isolated():
    article = make_article(
        source={"name": "Reuters"}, summary=["bad"], url=123,
        category=["Crypto"], assets=[None, {}, 123, "xbt", "BTC", " aapl ", ""],
    )

    assert article.source == "Unknown"
    assert article.summary == ""
    assert article.url == ""
    assert article.category == "Trad-Fi"
    assert article.assets == ["BTC", "AAPL"]
    assert make_article(assets="BTC").assets == []


@pytest.mark.parametrize("timestamp", [
    1_700_000_000, 1_700_000_000_000, "1700000000", "1700000000000",
    "2023-11-14T22:13:20Z", "2023-11-15T00:13:20+02:00",
    "2023-11-14T22:13:20", "Tue, 14 Nov 2023 22:13:20 GMT",
    datetime(2023, 11, 14, 22, 13, 20),
    datetime(2023, 11, 15, 0, 13, 20, tzinfo=timezone(timedelta(hours=2))),
])
def test_timestamps_become_aware_utc(timestamp):
    article = make_article(published_at=timestamp)

    assert article.published_at == datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
    assert article.published_at.tzinfo == timezone.utc


@pytest.mark.parametrize("timestamp", [None, "", "yesterday", "2026-99-99", True,
                                        {}, [], float("nan"), float("inf"), 10**100,
                                        pytest.param(10**10_000, id="huge-integer"),
                                        pytest.param("9" * 10_000, id="huge-numeric-string")])
def test_invalid_dates_stay_unknown(timestamp):
    assert make_article(published_at=timestamp).published_at is None


def test_unix_epoch_and_legacy_timestamp_field_are_supported():
    assert make_article(dt=0).published_at == datetime(1970, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(("fields", "category"), [
    ({"source": "CoinDesk", "title": "Sanctions affect bitcoin", "category": "Crypto"},
     "Geo-Politics"),
    ({"source": "CoinDesk", "category": "Trad-Fi", "title": "Bitcoin rally"}, "Trad-Fi"),
    ({"source": "CoinDesk/Editorial", "title": "Currency update"}, "Crypto"),
    ({"source": "Marketaux", "title": "Bitcoin rally"}, "FX/Macro"),
    ({"title": "Bitcoin ETF flows rise"}, "Crypto"),
    ({"title": "Crude oil and commodity markets fall"}, "FX/Macro"),
    ({"title": "Company earnings rise"}, "Trad-Fi"),
    ({"title": "Geopolitical tensions rise"}, "Geo-Politics"),
    ({"title": "Company reward and forward guidance", "category": "bad"}, "Trad-Fi"),
    ({"title": "The methods behind a research paper"}, "Trad-Fi"),
])
def test_category_precedence_and_word_boundaries(fields, category):
    assert make_article(**fields).category == category


def test_asset_names_and_canonical_pair_separators_match_without_mutating_cache():
    article = make_article(title="Bitcoin and Ethereum gain", assets=["AAPL"])
    result = match_article(
        article, [" xbt-usd ", "BTC_USD", "eth/usdt", "SOL/USD"],
        ["Bitcoin", "ETH", "AAPL", "ETH"],
    )

    assert result.matched is True
    assert result.match_terms == ["BTC/USD", "ETH/USDT", "BTC", "ETH", "AAPL"]
    assert article.matched is False
    assert article.match_terms == []
    result.assets.append("SOL")
    assert "SOL" not in article.assets


@pytest.mark.parametrize("title", ["XBT/USD jumps", "xbt-usd jumps", "BTC_USD jumps"])
def test_explicit_pair_aliases_and_separators(title):
    result = match_article(make_article(title=title), ["BTC/USD"])

    assert result.match_terms == ["BTC/USD"]


def test_matching_ignores_substrings_and_generic_quote_mentions():
    article = make_article(title="USD strengthens as methodical BTCC research continues")
    result = match_article(article, ["BTC/USD", "ETH/USD", "SOL/USD"], ["BTC", "ETH"])

    assert result.matched is False
    assert result.match_terms == []


def test_names_and_unknown_ticker_symbols_use_word_boundaries():
    article = make_article(title="Apple shares: AAPL leads while SOL rallies")

    assert match_article(article, ["AAPL/USD", "SOL_USD", "AA/USD"]).match_terms == [
        "AAPL/USD", "SOL/USD",
    ]
    generic_text = make_article(title="Follow this link for updates")
    assert match_article(generic_text, ["LINK/USD"]).matched is False


def test_bitcoin_cash_name_does_not_imply_a_bitcoin_match():
    article = make_article(title="Bitcoin Cash rallies")

    assert article.assets == ["BCH"]
    assert match_article(article, ["BTC/USD", "BCH/USD"]).match_terms == ["BCH/USD"]


def test_matching_ignores_malformed_requests_and_clears_previous_hits():
    article = make_article(title="Bitcoin rally")
    matched = match_article(article, ["BTC/USD"])
    result = match_article(matched, [None, "", "BTC/USD/ETH", "BTC"], [None, ""])

    assert result.matched is False
    assert result.match_terms == []
    assert matched.matched is True


def test_deduplication_keeps_first_exact_url_and_retains_variants_and_empty_urls():
    articles = [
        make_article(title="First", url=" https://example.com/story "),
        make_article(title="Duplicate", url="https://example.com/story"),
        make_article(title="Tracking variant", url="https://example.com/story?utm_source=news"),
        make_article(title="Case variant", url="https://EXAMPLE.com/story"),
        make_article(title="Trailing slash", url="https://example.com/story/"),
        make_article(title="No URL", url=""),
        make_article(title="Also no URL", url=""),
    ]

    result = deduplicate_articles(iter(articles))

    assert [article.title for article in result] == [
        "First", "Tracking variant", "Case variant", "Trailing slash", "No URL", "Also no URL",
    ]
    assert result[0] is articles[0]
    assert len(articles) == 7
