"""Provider contract tests using HTTP fixtures; no keys or live services needed."""

import asyncio
import os
import sys
import threading
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news import providers
from news.providers import build_providers

_KEYS = {
    "FINNHUB_KEY": "test-finnhub-secret",
    "CRYPTOPANIC_KEY": "test-cryptopanic-secret",
    "COINDESK_KEY": "test-coindesk-secret",
    "MESSARI_KEY": "test-messari-secret",
    "ALPACA_KEY": "test-alpaca-key",
    "ALPACA_SECRET": "test-alpaca-secret",
    "MARKETAUX_KEY": "test-marketaux-secret",
    "NEWSAPI_KEY": "test-newsapi-secret",
    "NEWS_YFINANCE_ENABLED": "false",
}
_DATE = "2026-09-21T12:00:00Z"
_URL = "https://example.com/article?keep=1"


def _provider(client, name, environ=None):
    env = _KEYS if environ is None else environ
    return next(provider for provider in build_providers(client, env) if provider.name == name)


@pytest.mark.asyncio
async def test_missing_credentials_and_yahoo_dependency_are_explicit(monkeypatch):
    monkeypatch.setattr(providers.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setenv("FINNHUB_KEY", "ambient-secret-must-not-be-used")
    async with httpx.AsyncClient() as client:
        configured = build_providers(client, {})
        assert len(configured) == 8
        assert all(not provider.enabled for provider in configured)
        by_name = {provider.name: provider for provider in configured}
        assert by_name["Finnhub"].disabled_reason == "missing_config:FINNHUB_KEY"
        assert by_name["Alpaca"].disabled_reason == "missing_config:ALPACA_KEY,ALPACA_SECRET"
        assert by_name["yFinance"].disabled_reason == "missing_dependency:yfinance"
        assert (await by_name["Finnhub"].fetch()).errors == ["disabled"]


@pytest.mark.asyncio
async def test_config_trims_keys_and_does_not_expose_credentials():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = _provider(client, "Finnhub", {"FINNHUB_KEY": "  private-key  "})
        assert provider.enabled
        assert "private-key" not in repr(provider)
        await provider.fetch()
    assert requests[0].headers["X-Finnhub-Token"] == "private-key"
    assert "private-key" not in str(requests[0].url)


@pytest.mark.asyncio
async def test_finnhub_preserves_first_category_when_second_fails():
    def handle(request):
        if request.url.params["category"] == "crypto":
            return httpx.Response(429, json={"error": "upstream-sensitive-message"})
        return httpx.Response(200, json=[{
            "headline": "Markets rise", "summary": "Summary", "source": "Wire",
            "url": _URL, "datetime": 1789992000,
        }])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await _provider(client, "Finnhub").fetch()
    assert result.errors == ["crypto:http_429"]
    assert result.articles == [{
        "source": "Finnhub/Wire", "title": "Markets rise", "summary": "Summary",
        "url": _URL, "published_at": 1789992000, "category": "Trad-Fi", "assets": [],
    }]


@pytest.mark.parametrize("name,path,payload,source,timestamp,assets", [
    (
        "CryptoPanic", "/api/growth/v2/posts/",
        {"results": [{"title": "Headline", "description": "Summary", "url": _URL,
                      "published_at": _DATE, "currencies": [{"code": "BTC"}]}]},
        "CryptoPanic", _DATE, ["BTC"],
    ),
    (
        "CoinDesk", "/news/v1/article/list",
        {"Data": [{"TITLE": "Headline", "BODY": "Summary", "URL": _URL,
                   "PUBLISHED_ON": 1789992000}]},
        "CoinDesk", 1789992000, [],
    ),
    (
        "Messari", "/news/v1/news/feed",
        {"data": [{"title": "Headline", "description": "Summary", "url": _URL,
                   "publishTime": _DATE, "assets": [{"symbol": "ETH"}]}]},
        "Messari", _DATE, ["ETH"],
    ),
    (
        "Alpaca", "/v1beta1/news",
        {"news": [{"headline": "Headline", "summary": "Summary", "url": _URL,
                   "source": "Benzinga", "created_at": _DATE, "symbols": ["AAPL"]}]},
        "Alpaca/Benzinga", _DATE, ["AAPL"],
    ),
    (
        "Marketaux", "/v1/news/all",
        {"data": [{"title": "Headline", "description": "Summary", "url": _URL,
                   "published_at": _DATE, "entities": [{"symbol": "MSFT"}]}]},
        "Marketaux", _DATE, ["MSFT"],
    ),
    (
        "NewsAPI", "/v2/top-headlines",
        {"status": "ok", "articles": [{"title": "Headline", "description": "Summary",
                                        "url": _URL, "publishedAt": _DATE,
                                        "source": {"name": "Wire"}}]},
        "NewsAPI/Wire", _DATE, [],
    ),
])
@pytest.mark.asyncio
async def test_http_adapters_preserve_fields_and_provider_assets(
    name, path, payload, source, timestamp, assets
):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await _provider(client, name).fetch()
    assert result.errors == []
    assert len(result.articles) == 1
    assert result.articles[0] == {
        "source": source, "title": "Headline", "summary": "Summary", "url": _URL,
        "published_at": timestamp, "category": "", "assets": assets,
    }
    request = requests[0]
    assert request.url.path == path
    assert request.extensions["timeout"]["read"] == 8.0
    if name == "CryptoPanic":
        assert request.url.params["auth_token"] == _KEYS["CRYPTOPANIC_KEY"]
    elif name == "CoinDesk":
        assert request.headers["Authorization"] == f"Apikey {_KEYS['COINDESK_KEY']}"
    elif name == "Messari":
        assert request.headers["X-Messari-API-Key"] == _KEYS["MESSARI_KEY"]
    elif name == "Alpaca":
        assert request.headers["APCA-API-SECRET-KEY"] == _KEYS["ALPACA_SECRET"]
    elif name == "Marketaux":
        assert request.url.params["api_token"] == _KEYS["MARKETAUX_KEY"]
    elif name == "NewsAPI":
        assert request.headers["X-Api-Key"] == _KEYS["NEWSAPI_KEY"]
        assert request.url.params["country"] == "us"
        assert "language" not in request.url.params


@pytest.mark.parametrize("payload,expected_error", [
    ({"status": "error", "message": "secret", "articles": []}, "api_error"),
    ({"articles": None}, "invalid_response"),
    ([], "invalid_response"),
    ({"unexpected": []}, "invalid_response"),
])
@pytest.mark.asyncio
async def test_invalid_or_error_payloads_are_not_reported_as_success(payload, expected_error):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await _provider(client, "NewsAPI").fetch()
    assert result.articles == []
    assert result.errors == [expected_error]


@pytest.mark.asyncio
async def test_mixed_items_preserve_valid_articles_and_null_nested_source():
    payload = {"articles": [None, "bad", {
        "title": "Valid", "source": None, "url": _URL, "publishedAt": _DATE,
    }]}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await _provider(client, "NewsAPI").fetch()
    assert len(result.articles) == 1
    assert result.articles[0]["source"] == "NewsAPI/NewsAPI"
    assert result.errors == ["invalid_item"]


@pytest.mark.asyncio
async def test_provider_api_warning_preserves_returned_articles():
    payload = {"Data": [{"TITLE": "Partial response", "URL": _URL}],
               "Err": {"message": "sensitive-provider-detail"}}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await _provider(client, "CoinDesk").fetch()
    assert len(result.articles) == 1
    assert result.errors == ["api_error"]


@pytest.mark.parametrize("failure,expected", [
    ("http", "http_401"),
    ("timeout", "timeout"),
    ("connection", "request_error"),
    ("json", "invalid_response"),
])
@pytest.mark.asyncio
async def test_errors_never_include_urls_credentials_or_payloads(failure, expected):
    def handle(request):
        secret_message = f"{request.url} secret-provider-message"
        if failure == "timeout":
            raise httpx.ReadTimeout(secret_message, request=request)
        if failure == "connection":
            raise httpx.ConnectError(secret_message, request=request)
        if failure == "json":
            return httpx.Response(200, text=secret_message)
        return httpx.Response(401, text=secret_message)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await _provider(client, "Marketaux").fetch()
    assert result.articles == []
    assert result.errors == [expected]


@pytest.mark.asyncio
async def test_invalid_plan_and_yahoo_setting_are_disabled_without_echoing_values():
    async with httpx.AsyncClient() as client:
        env = dict(_KEYS, CRYPTOPANIC_PLAN="https://private-host/secret", NEWS_YFINANCE_ENABLED="secret")
        crypto = _provider(client, "CryptoPanic", env)
        yahoo = _provider(client, "yFinance", env)
    assert not crypto.enabled and crypto.disabled_reason == "invalid_config:CRYPTOPANIC_PLAN"
    assert not yahoo.enabled and yahoo.disabled_reason == "invalid_config:NEWS_YFINANCE_ENABLED"


@pytest.mark.asyncio
async def test_yahoo_runs_off_loop_and_accepts_current_and_legacy_records(monkeypatch):
    loop_thread = threading.get_ident()
    threads = []
    seen_tickers = []
    session = SimpleNamespace(__enter__=lambda: None)

    class Session:
        def __init__(self, deadline):
            pass

        def __enter__(self):
            return session

        def __exit__(self, *args):
            pass

    class Ticker:
        def __init__(self, ticker, session):
            seen_tickers.append(ticker)

        def get_news(self, count):
            threads.append(threading.get_ident())
            if len(seen_tickers) > 1:
                raise RuntimeError("sensitive-provider-error")
            return [
                {"title": "Legacy", "publisher": "Wire", "link": _URL,
                 "providerPublishTime": 1789992000, "relatedTickers": ["BTC-USD"]},
                {"content": {"title": "Current", "summary": "Summary", "pubDate": _DATE,
                             "provider": {"displayName": "Yahoo Finance"},
                             "canonicalUrl": {"url": _URL},
                             "relatedTickers": [{"symbol": "ETH-USD"}]}},
                {"ad": {"id": "skip-this"}},
            ]

    monkeypatch.setattr(providers.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(providers.importlib, "import_module", lambda name: SimpleNamespace(Ticker=Ticker))
    monkeypatch.setattr(providers, "_yahoo_session", Session)
    async with httpx.AsyncClient() as client:
        result = await _provider(client, "yFinance", {}).fetch()
    assert len(result.articles) == 2
    assert result.articles[0]["title"] == "Legacy"
    assert result.articles[0]["published_at"] == 1789992000
    assert result.articles[1]["source"] == "yFinance/Yahoo Finance"
    assert result.articles[1]["published_at"] == _DATE
    assert result.articles[1]["assets"] == ["ETH-USD"]
    assert all(thread != loop_thread for thread in threads)
    assert len(result.errors) == 7
    assert "sensitive" not in repr(result.errors)
    # Identical URLs intentionally survive the adapter; service owns deduplication.
    assert result.articles[0]["url"] == result.articles[1]["url"]


def test_yahoo_batch_deadline_preserves_completed_tickers(monkeypatch):
    now = [0.0]

    class Session:
        def __init__(self, deadline):
            assert deadline == 20.0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Ticker:
        def __init__(self, ticker, session):
            pass

        def get_news(self, count):
            now[0] = 21.0
            return [{"title": "Saved before deadline", "link": _URL}]

    monkeypatch.setattr(providers.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(providers.importlib, "import_module", lambda name: SimpleNamespace(Ticker=Ticker))
    monkeypatch.setattr(providers, "_yahoo_session", Session)
    result = providers._fetch_yfinance_sync(threading.Event())
    assert len(result.articles) == 1
    assert result.errors == ["batch:timeout"]


def test_yahoo_session_caps_request_timeout_and_enforces_batch_deadline(monkeypatch):
    now = [10.0]
    captured = []

    class Session:
        def __init__(self, **kwargs):
            pass

        def request(self, method, url, *args, **kwargs):
            captured.append(kwargs["timeout"])
            return "response"

    monkeypatch.setitem(sys.modules, "curl_cffi", SimpleNamespace(requests=SimpleNamespace(Session=Session)))
    monkeypatch.setattr(providers.time, "monotonic", lambda: now[0])
    session = providers._yahoo_session(deadline=20.0)
    assert session.request("GET", "https://example.com", timeout=30) == "response"
    now[0] = 19.0
    assert session.request("GET", "https://example.com", timeout=30) == "response"
    assert captured == [8.0, 1.0]
    now[0] = 20.0
    with pytest.raises(TimeoutError):
        session.request("GET", "https://example.com")


@pytest.mark.parametrize("response,expected_error", [
    (httpx.Response(200, text="sensitive invalid JSON"), "invalid_response"),
    (httpx.Response(200, json={}), "invalid_response"),
    (httpx.Response(200, json={"data": {}}), "invalid_response"),
    (httpx.Response(200, json={"data": {"tickerStream": {}}}), "invalid_response"),
    (httpx.Response(200, json={"data": {"tickerStream": {"stream": None}}}), "invalid_response"),
    (httpx.Response(200, json={"data": {"tickerStream": {"stream": {}}}}), "invalid_response"),
    (httpx.Response(429, text="sensitive upstream details"), "http_429"),
    (httpx.Response(200, json={"errors": ["sensitive upstream error"],
                              "data": {"tickerStream": {"stream": []}}}), "api_error"),
    (httpx.Response(200, json={"data": {"tickerStream": {"stream": []}}}), None),
])
def test_yahoo_feed_validation_prevents_false_healthy_empty_results(
    monkeypatch, response, expected_error
):
    class Session:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, method, url, *args, **kwargs):
            return response

    class Ticker:
        def __init__(self, ticker, session):
            self.session = session

        def get_news(self, count):
            result = self.session.request("POST", "https://finance.yahoo.com/xhr/ncp?queryRef=latestNews")
            # Mirror yfinance's suppression to demonstrate interception occurs
            # before either malformed JSON or missing feed keys can become [].
            try:
                payload = result.json()
            except ValueError:
                payload = {}
            return payload.get("data", {}).get("tickerStream", {}).get("stream", [])

    monkeypatch.setitem(sys.modules, "curl_cffi", SimpleNamespace(requests=SimpleNamespace(Session=Session)))
    monkeypatch.setattr(providers.importlib, "import_module", lambda name: SimpleNamespace(Ticker=Ticker))
    monkeypatch.setattr(providers, "_YAHOO_TICKERS", (("BTC-USD", "Crypto"),))
    result = providers._fetch_yfinance_sync(threading.Event())
    assert result.articles == []
    assert result.errors == ([f"BTC-USD:{expected_error}"] if expected_error else [])


def test_yahoo_session_leaves_cookie_and_crumb_responses_unchecked(monkeypatch):
    response = httpx.Response(200, text="crumb-token-not-json")

    class Session:
        def __init__(self, **kwargs):
            pass

        def request(self, method, url, *args, **kwargs):
            return response

    monkeypatch.setitem(sys.modules, "curl_cffi", SimpleNamespace(requests=SimpleNamespace(Session=Session)))
    monkeypatch.setattr(providers.time, "monotonic", lambda: 10.0)
    session = providers._yahoo_session(deadline=20.0)
    assert session.request("GET", "https://query1.finance.yahoo.com/v1/test/getcrumb") is response


@pytest.mark.asyncio
async def test_cancelled_yahoo_batch_does_not_start_a_second_worker(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def blocked_fetch(stop):
        entered.set()
        try:
            release.wait(timeout=3)
            assert stop.is_set()
            return providers.ProviderResult([])
        finally:
            finished.set()

    monkeypatch.setattr(providers, "_fetch_yfinance_sync", blocked_fetch)
    fetch = providers._yfinance_fetcher()
    task = asyncio.create_task(fetch())
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        result = await fetch()
        assert result.errors == ["previous_request_running"]
    finally:
        release.set()
        assert await asyncio.to_thread(finished.wait, 2)
