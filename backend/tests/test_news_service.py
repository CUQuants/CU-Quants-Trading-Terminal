"""News refresh, cache, and health tests with offline provider responses."""

import asyncio
import os
import sys
from datetime import datetime, timezone

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.providers import NewsProvider, ProviderResult
from news.service import NewsService


def article(title, url, *, source="Example", category="Crypto", day=1):
    return {
        "source": source,
        "title": title,
        "summary": "Market update",
        "url": url,
        "published_at": datetime(2020, 1, day, tzinfo=timezone.utc),
        "category": category,
    }


class ScriptedProvider:
    """Return successive refresh results without opening a network connection."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    async def fetch(self):
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


def statuses(service):
    return {provider.name: provider for provider in service.get_status().providers}


@pytest.mark.asyncio
async def test_refresh_caches_normalized_articles_and_records_health():
    fake = ScriptedProvider(ProviderResult([
        article("Bitcoin update", "https://example.test/old", day=1),
        article("Ethereum update", "https://example.test/new", day=2),
    ]))
    service = NewsService([NewsProvider("Example", fake.fetch)])
    try:
        assert service.get_articles() == []
        assert statuses(service)["Example"].state == "pending"
        assert service.get_status().refresh_interval_seconds == 300

        await service.refresh()

        assert [item.title for item in service.get_articles()] == [
            "Ethereum update", "Bitcoin update",
        ]
        health = statuses(service)["Example"]
        assert health.state == "ok"
        assert health.article_count == 2
        assert health.last_attempt is not None
        assert health.last_success is not None
        assert health.last_error is None
        assert health.consecutive_failures == 0
        assert health.total_failures == 0
        assert not health.stale
        status = service.get_status()
        assert status.article_count == 2
        assert status.last_refresh is not None
        assert status.last_success is not None
        assert not status.refreshing
        assert not status.stale
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_disabled_providers_are_visible_but_never_called():
    fake = ScriptedProvider(AssertionError("Disabled provider was called"))
    service = NewsService([
        NewsProvider("Optional", fake.fetch, enabled=False,
                     disabled_reason="API key is not configured"),
    ])
    try:
        await service.refresh()
        health = statuses(service)["Optional"]
        assert fake.calls == 0
        assert health.state == "disabled"
        assert not health.enabled
        assert health.disabled_reason == "API key is not configured"
        assert health.last_attempt is None
        assert health.total_failures == 0
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_provider_failure_keeps_last_good_cache_and_other_provider_healthy():
    unreliable = ScriptedProvider(
        ProviderResult([article("Bitcoin old", "https://example.test/one")]),
        RuntimeError("token=do-not-expose"),
        ProviderResult([article("Bitcoin recovered", "https://example.test/three")]),
    )
    healthy = ScriptedProvider(
        ProviderResult([article("Ethereum old", "https://example.test/two")]),
        ProviderResult([article("Ethereum current", "https://example.test/four")]),
    )
    service = NewsService([
        NewsProvider("Unreliable", unreliable.fetch),
        NewsProvider("Healthy", healthy.fetch),
    ])
    try:
        await service.refresh()
        last_success = statuses(service)["Unreliable"].last_success
        await service.refresh()

        assert {item.title for item in service.get_articles()} == {
            "Bitcoin old", "Ethereum current",
        }
        failed = statuses(service)["Unreliable"]
        assert failed.state == "error"
        assert failed.last_success == last_success
        assert failed.consecutive_failures == 1
        assert failed.total_failures == 1
        assert failed.stale
        assert "do-not-expose" not in service.get_status().model_dump_json()
        assert statuses(service)["Healthy"].state == "ok"

        await service.refresh()

        recovered = statuses(service)["Unreliable"]
        assert recovered.state == "ok"
        assert recovered.consecutive_failures == 0
        assert recovered.total_failures == 1
        assert recovered.last_error is None
        assert not recovered.stale
        assert "Bitcoin old" not in {item.title for item in service.get_articles()}
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_partial_failure_merges_new_articles_with_last_good_snapshot():
    fake = ScriptedProvider(
        ProviderResult([article("Bitcoin old", "https://example.test/old")]),
        ProviderResult(
            [article("Bitcoin current", "https://example.test/current")],
            errors=["TimeoutError"],
        ),
    )
    service = NewsService([NewsProvider("Example", fake.fetch)])
    try:
        await service.refresh()
        await service.refresh()
        assert {item.url for item in service.get_articles()} == {
            "https://example.test/old", "https://example.test/current",
        }
        health = statuses(service)["Example"]
        assert health.state == "degraded"
        assert health.total_failures == 1
        assert health.consecutive_failures == 1
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_successful_empty_result_clears_previous_provider_snapshot():
    fake = ScriptedProvider(
        ProviderResult([article("Bitcoin old", "https://example.test/old")]),
        ProviderResult([]),
    )
    service = NewsService([NewsProvider("Example", fake.fetch)])
    try:
        await service.refresh()
        await service.refresh()
        assert service.get_articles() == []
        assert statuses(service)["Example"].state == "ok"
        assert statuses(service)["Example"].article_count == 0
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_invalid_rows_are_isolated_and_all_invalid_refresh_is_a_failure():
    fake = ScriptedProvider(
        ProviderResult([None, article("Bitcoin valid", "https://example.test/valid")]),
        ProviderResult([None]),
    )
    service = NewsService([NewsProvider("Example", fake.fetch)])
    try:
        await service.refresh()
        assert [item.title for item in service.get_articles()] == ["Bitcoin valid"]
        assert statuses(service)["Example"].state == "degraded"

        await service.refresh()
        assert [item.title for item in service.get_articles()] == ["Bitcoin valid"]
        assert statuses(service)["Example"].state == "error"
        assert statuses(service)["Example"].total_failures == 2
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_failed_snapshot_expires_by_fetch_time_not_article_publication():
    fake = ScriptedProvider(
        ProviderResult([article("Bitcoin historic", "https://example.test/historic")]),
        RuntimeError("offline"),
    )
    service = NewsService([NewsProvider("Example", fake.fetch)], cache_ttl=0.04)
    try:
        await service.refresh()
        assert len(service.get_articles()) == 1
        await asyncio.sleep(0.05)
        await service.refresh()
        assert service.get_articles() == []
        assert statuses(service)["Example"].state == "error"
        assert statuses(service)["Example"].stale
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_cache_is_bounded_and_newest_articles_are_retained():
    fake = ScriptedProvider(ProviderResult([
        article("Bitcoin first", "https://example.test/1", day=1),
        article("Bitcoin third", "https://example.test/3", day=3),
        article("Bitcoin second", "https://example.test/2", day=2),
    ]))
    service = NewsService([NewsProvider("Example", fake.fetch)], max_articles=2)
    try:
        await service.refresh()
        assert [item.title for item in service.get_articles()] == [
            "Bitcoin third", "Bitcoin second",
        ]
        assert service.get_status().article_count == 2
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_exact_url_dedup_uses_first_completed_provider_and_keeps_blank_urls():
    fast_finished = asyncio.Event()

    async def slow():
        await fast_finished.wait()
        await asyncio.sleep(0)
        return ProviderResult([
            article("Slow duplicate", "https://example.test/shared"),
            article("Slow no URL", ""),
            article("Query variant", "https://example.test/shared?ref=other"),
        ])

    async def fast():
        fast_finished.set()
        return ProviderResult([
            article("Fast winner", "https://example.test/shared"),
            article("Fast no URL", ""),
        ])

    service = NewsService([NewsProvider("Slow", slow), NewsProvider("Fast", fast)])
    try:
        await service.refresh()
        assert {item.title for item in service.get_articles()} == {
            "Fast winner", "Slow no URL", "Fast no URL", "Query variant",
        }
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_overlapping_refresh_skips_and_cache_replacement_is_atomic():
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        if calls > 1:
            entered.set()
            await release.wait()
        return ProviderResult([
            article(f"Bitcoin refresh {calls}", f"https://example.test/{calls}"),
        ])

    service = NewsService([NewsProvider("Example", fetch)])
    refresh_task = None
    try:
        await service.refresh()
        refresh_task = asyncio.create_task(service.refresh())
        await asyncio.wait_for(entered.wait(), timeout=1)
        assert service.get_status().refreshing
        assert [item.title for item in service.get_articles()] == ["Bitcoin refresh 1"]

        await asyncio.wait_for(service.refresh(), timeout=0.2)
        assert calls == 2
        assert [item.title for item in service.get_articles()] == ["Bitcoin refresh 1"]

        release.set()
        await asyncio.wait_for(refresh_task, timeout=1)
        assert [item.title for item in service.get_articles()] == ["Bitcoin refresh 2"]
        assert not service.get_status().refreshing
    finally:
        release.set()
        if refresh_task is not None:
            await refresh_task
        await service.aclose()


@pytest.mark.asyncio
async def test_provider_timeout_is_reported_without_blocking_healthy_provider():
    async def stalled():
        await asyncio.Event().wait()

    healthy = ScriptedProvider(ProviderResult([
        article("Bitcoin healthy", "https://example.test/healthy"),
    ]))
    service = NewsService([
        NewsProvider("Stalled", stalled), NewsProvider("Healthy", healthy.fetch),
    ], provider_timeout=0.01)
    try:
        await asyncio.wait_for(service.refresh(), timeout=1)
        assert statuses(service)["Stalled"].state == "error"
        assert statuses(service)["Healthy"].state == "ok"
        assert [item.title for item in service.get_articles()] == ["Bitcoin healthy"]
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_http_failure_reports_status_without_exposing_request_credentials():
    request = httpx.Request("GET", "https://example.test/news?token=private-key")
    response = httpx.Response(429, request=request)
    fake = ScriptedProvider(httpx.HTTPStatusError(
        "private-key was rejected", request=request, response=response,
    ))
    service = NewsService([NewsProvider("Example", fake.fetch)])
    try:
        await service.refresh()
        status = service.get_status()
        assert "429" in status.providers[0].last_error
        assert "private-key" not in status.model_dump_json()
        assert "https://example.test" not in status.model_dump_json()
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_default_scheduler_waits_five_minutes_between_refresh_starts(monkeypatch):
    sleeping = asyncio.Event()
    delays = []

    async def wait_interval(delay):
        delays.append(delay)
        sleeping.set()
        await asyncio.Event().wait()

    fake = ScriptedProvider(ProviderResult([]))
    service = NewsService([NewsProvider("Example", fake.fetch)])
    monkeypatch.setattr("news.service.asyncio.sleep", wait_interval)
    try:
        service.start()
        await asyncio.wait_for(sleeping.wait(), timeout=1)
        assert fake.calls == 1
        assert delays[0] == pytest.approx(300, abs=1)
    finally:
        await service.aclose()


@pytest.mark.asyncio
async def test_scheduler_refreshes_immediately_repeats_and_stops_on_close():
    refreshed_twice = asyncio.Event()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        if calls >= 2:
            refreshed_twice.set()
        return ProviderResult([])

    service = NewsService([NewsProvider("Example", fetch)], refresh_interval=0.02)
    try:
        service.start()
        service.start()
        await asyncio.wait_for(refreshed_twice.wait(), timeout=1)
        assert calls == 2
        assert service.get_status().next_refresh is not None
    finally:
        await service.aclose()
    calls_at_close = calls
    await asyncio.sleep(0.03)
    assert calls == calls_at_close


@pytest.mark.asyncio
async def test_closing_scheduler_cancels_in_flight_provider_fetch():
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def fetch():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    service = NewsService([NewsProvider("Example", fetch)])
    try:
        service.start()
        await asyncio.wait_for(entered.wait(), timeout=1)
    finally:
        await asyncio.wait_for(service.aclose(), timeout=1)
    assert cancelled.is_set()
    assert not service.get_status().refreshing
    assert service.get_status().next_refresh is None


@pytest.mark.asyncio
async def test_service_close_preserves_caller_owned_http_client():
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=[]),
    ))
    service = NewsService([], client=client)
    try:
        await service.refresh()
        await service.aclose()
        assert not client.is_closed
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_filters_pagination_and_matching_do_not_mutate_shared_cache():
    fake = ScriptedProvider(ProviderResult([
        article("Bitcoin mining update", "https://example.test/btc", source="CoinDesk", day=3),
        article("Ethereum staking update", "https://example.test/eth", source="Messari", day=2),
        article("Company earnings report", "https://example.test/equity",
                source="Reuters", category="Trad-Fi", day=1),
    ]))
    service = NewsService([NewsProvider("Example", fake.fetch)])
    try:
        await service.refresh()
        before = [item.model_dump() for item in service.get_articles()]
        bitcoin = service.get_articles(pairs=["BTC/USD"], matched_only=True)
        assert [item.title for item in bitcoin] == ["Bitcoin mining update"]
        assert bitcoin[0].matched
        assert bitcoin[0].match_terms
        assert [item.title for item in service.get_articles(assets=["ETH"], matched_only=True)] == [
            "Ethereum staking update",
        ]
        assert len(service.get_articles(category="Crypto")) == 2
        assert len(service.get_articles(category="All")) == 3
        assert [item.source for item in service.get_articles(source="Reuters")] == ["Reuters"]
        assert [item.title for item in service.get_articles(query="STAKING")] == [
            "Ethereum staking update",
        ]
        assert [item.title for item in service.get_articles(limit=1, offset=1)] == [
            "Ethereum staking update",
        ]
        bitcoin[0].title = "Changed by caller"
        bitcoin[0].assets.append("FAKE")
        assert [item.model_dump() for item in service.get_articles()] == before
    finally:
        await service.aclose()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, 300), ("", 300), ("120", 120), ("45.5", 45.5),
     ("abc", 300), ("nan", 300), ("10", 300), ("3600", 300), ("-5", 300)],
)
def test_refresh_interval_reads_env_and_falls_back_on_invalid(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("NEWS_REFRESH_SECONDS", raising=False)
    else:
        monkeypatch.setenv("NEWS_REFRESH_SECONDS", raw)
    service = NewsService([])
    assert service.get_status().refresh_interval_seconds == expected


def test_explicit_refresh_interval_overrides_env(monkeypatch):
    monkeypatch.setenv("NEWS_REFRESH_SECONDS", "120")
    service = NewsService([], refresh_interval=0.5)
    assert service.get_status().refresh_interval_seconds == 0.5
