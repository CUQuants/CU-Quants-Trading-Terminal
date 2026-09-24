"""Async adapters for the eight XLRTS News Hub providers.

Adapters only translate provider fields. NewsService owns normalization, exact
URL deduplication, refresh scheduling, health, and the shared article cache.
Configuration is read when providers are built, never at module import time.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import os
import threading
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from functools import partial
from typing import Any
from urllib.parse import urlsplit

import httpx

_REQUEST_TIMEOUT = 8.0
_YAHOO_BATCH_TIMEOUT = 20.0
_YAHOO_TICKERS = (
    ("BTC-USD", "Crypto"),
    ("ETH-USD", "Crypto"),
    ("^GSPC", "Trad-Fi"),
    ("^DJI", "Trad-Fi"),
    ("^IXIC", "Trad-Fi"),
    ("EURUSD=X", "FX/Macro"),
    ("GC=F", "FX/Macro"),
    ("CL=F", "FX/Macro"),
)


@dataclass
class ProviderResult:
    """Raw articles and safe failure codes, including partial successes."""

    articles: list[dict]
    errors: list[str] = field(default_factory=list)


@dataclass
class NewsProvider:
    """A provider's configuration and asynchronous fetch operation."""

    name: str
    fetch: Callable[[], Awaitable[ProviderResult]] = field(repr=False)
    enabled: bool = True
    disabled_reason: str | None = None


class _ProviderResponseError(Exception):
    """An adapter-generated failure whose message contains only a safe code."""


def _error_code(exc: Exception) -> str:
    # Exception messages can contain request URLs, including query-string keys.
    if isinstance(exc, _ProviderResponseError):
        return str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http_{exc.response.status_code}"
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return "timeout"
    if isinstance(exc, httpx.RequestError):
        return "request_error"
    if isinstance(exc, ValueError):
        return "invalid_response"
    return "provider_error"


async def _get_items(
    client: httpx.AsyncClient,
    url: str,
    result_key: str | None,
    *,
    params: dict | None = None,
    headers: dict | None = None,
) -> tuple[list[dict], list[str]]:
    try:
        response = await client.get(
            url, params=params, headers=headers, timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return [], [_error_code(exc)]

    errors = []
    if isinstance(payload, dict) and (
        payload.get("error")
        or payload.get("Err")
        or payload.get("status") == "error"
    ):
        errors.append("api_error")
    if result_key is not None:
        if not isinstance(payload, dict):
            return [], errors or ["invalid_response"]
        payload = payload.get(result_key)
    if not isinstance(payload, list):
        return [], errors or ["invalid_response"]
    items = [item for item in payload if isinstance(item, dict)]
    if len(items) != len(payload):
        errors.append("invalid_item")
    return items, errors


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _symbols(value: Any, key: str | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    if key:
        return [
            item[key]
            for item in value
            if isinstance(item, dict) and isinstance(item.get(key), str)
        ]
    return [item for item in value if isinstance(item, str)]


def _article(
    source: str,
    title: Any,
    summary: Any,
    url: Any,
    published_at: Any,
    *,
    category: str = "",
    assets: list[str] | None = None,
) -> dict:
    return {
        "source": source,
        "title": title,
        "summary": summary,
        "url": url,
        "published_at": published_at,
        "category": category,
        "assets": assets or [],
    }


async def _fetch_finnhub(client: httpx.AsyncClient, key: str) -> ProviderResult:
    result = ProviderResult([])
    for category, label in (("general", "Trad-Fi"), ("crypto", "Crypto")):
        items, errors = await _get_items(
            client,
            "https://finnhub.io/api/v1/news",
            None,
            params={"category": category},
            headers={"X-Finnhub-Token": key},
        )
        result.errors.extend(f"{category}:{error}" for error in errors)
        for item in items:
            source = _text(item.get("source"), category)
            result.articles.append(_article(
                f"Finnhub/{source}", item.get("headline"), item.get("summary"),
                item.get("url"), item.get("datetime"), category=label,
            ))
    return result


async def _fetch_cryptopanic(
    client: httpx.AsyncClient, key: str, plan: str
) -> ProviderResult:
    items, errors = await _get_items(
        client,
        f"https://cryptopanic.com/api/{plan}/v2/posts/",
        "results",
        params={"auth_token": key, "public": "true", "kind": "news"},
    )
    articles = [
        _article(
            "CryptoPanic", item.get("title"), item.get("description", ""),
            item.get("original_url") or item.get("url"), item.get("published_at"),
            assets=_symbols(item.get("currencies"), "code"),
        )
        for item in items
    ]
    return ProviderResult(articles, errors)


async def _fetch_coindesk(client: httpx.AsyncClient, key: str) -> ProviderResult:
    items, errors = await _get_items(
        client,
        "https://data-api.coindesk.com/news/v1/article/list",
        "Data",
        params={"lang": "EN", "limit": 20},
        headers={"Authorization": f"Apikey {key}"},
    )
    articles = [
        _article(
            "CoinDesk", item.get("TITLE"), _text(item.get("BODY"))[:300],
            item.get("URL"), item.get("PUBLISHED_ON"),
        )
        for item in items
    ]
    return ProviderResult(articles, errors)


async def _fetch_messari(client: httpx.AsyncClient, key: str) -> ProviderResult:
    items, errors = await _get_items(
        client,
        "https://api.messari.io/news/v1/news/feed",
        "data",
        params={"limit": 20},
        headers={"X-Messari-API-Key": key},
    )
    articles = [
        _article(
            "Messari", item.get("title"), _text(item.get("description"))[:300],
            item.get("url"), item.get("publishTime") or item.get("publishTimeMillis"),
            assets=_symbols(item.get("assets"), "symbol"),
        )
        for item in items
    ]
    return ProviderResult(articles, errors)


async def _fetch_alpaca(
    client: httpx.AsyncClient, key: str, secret: str
) -> ProviderResult:
    items, errors = await _get_items(
        client,
        "https://data.alpaca.markets/v1beta1/news",
        "news",
        params={"limit": 20},
        headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
    )
    articles = [
        _article(
            f"Alpaca/{_text(item.get('source'), 'news')}",
            item.get("headline"), item.get("summary"), item.get("url"),
            item.get("created_at"), assets=_symbols(item.get("symbols")),
        )
        for item in items
    ]
    return ProviderResult(articles, errors)


async def _fetch_marketaux(client: httpx.AsyncClient, key: str) -> ProviderResult:
    items, errors = await _get_items(
        client,
        "https://api.marketaux.com/v1/news/all",
        "data",
        params={"api_token": key, "language": "en", "limit": 10},
    )
    articles = [
        _article(
            "Marketaux", item.get("title"), item.get("description"),
            item.get("url"), item.get("published_at"),
            assets=_symbols(item.get("entities"), "symbol"),
        )
        for item in items
    ]
    return ProviderResult(articles, errors)


async def _fetch_newsapi(client: httpx.AsyncClient, key: str) -> ProviderResult:
    items, errors = await _get_items(
        client,
        "https://newsapi.org/v2/top-headlines",
        "articles",
        params={"category": "business", "country": "us", "pageSize": 20},
        headers={"X-Api-Key": key},
    )
    articles = []
    for item in items:
        source = item.get("source")
        publisher = source.get("name") if isinstance(source, dict) else None
        articles.append(_article(
            f"NewsAPI/{_text(publisher, 'NewsAPI')}", item.get("title"),
            item.get("description"), item.get("url"), item.get("publishedAt"),
        ))
    return ProviderResult(articles, errors)


def _yahoo_article(item: dict, category: str) -> dict:
    """Accept both Yahoo's nested content records and the legacy flat schema."""
    content = item.get("content")
    if not isinstance(content, dict):
        return _article(
            f"yFinance/{_text(item.get('publisher'), 'Yahoo')}",
            item.get("title"), item.get("summary", ""), item.get("link"),
            item.get("providerPublishTime"), category=category,
            assets=_symbols(item.get("relatedTickers")),
        )
    provider = content.get("provider")
    publisher = provider.get("displayName") if isinstance(provider, dict) else None
    canonical_url = content.get("canonicalUrl")
    clickthrough_url = content.get("clickThroughUrl")
    url = canonical_url.get("url") if isinstance(canonical_url, dict) else None
    if not url and isinstance(clickthrough_url, dict):
        url = clickthrough_url.get("url")
    return _article(
        f"yFinance/{_text(publisher, 'Yahoo')}", content.get("title"),
        content.get("summary", ""), url, content.get("pubDate"),
        category=category, assets=_symbols(content.get("relatedTickers"), "symbol"),
    )


def _yahoo_session(deadline: float):
    from curl_cffi import requests

    class BoundedSession(requests.Session):
        def request(self, method, url, *args, **kwargs):
            # yfinance supplies its own per-request defaults; cap those too.
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            kwargs["timeout"] = min(_REQUEST_TIMEOUT, remaining)
            response = super().request(method, url, *args, **kwargs)
            parsed_url = urlsplit(url)
            if parsed_url.hostname == "finance.yahoo.com" and parsed_url.path == "/xhr/ncp":
                _validate_yahoo_response(response)
            return response

    return BoundedSession(impersonate="chrome")


def _validate_yahoo_response(response) -> None:
    # get_news can suppress malformed JSON and missing feed keys into []. Check
    # only its news response here, leaving cookie and crumb requests unchanged.
    if not 200 <= response.status_code < 300:
        raise _ProviderResponseError(f"http_{response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        raise _ProviderResponseError("invalid_response") from None
    if isinstance(payload, dict) and (payload.get("error") or payload.get("errors")):
        raise _ProviderResponseError("api_error")
    for key in ("data", "tickerStream", "stream"):
        if not isinstance(payload, dict) or key not in payload:
            raise _ProviderResponseError("invalid_response")
        payload = payload[key]
    if not isinstance(payload, list):
        raise _ProviderResponseError("invalid_response")


def _fetch_yfinance_sync(stop: threading.Event) -> ProviderResult:
    deadline = time.monotonic() + _YAHOO_BATCH_TIMEOUT
    yf = importlib.import_module("yfinance")
    result = ProviderResult([])
    with _yahoo_session(deadline) as session:
        for ticker, category in _YAHOO_TICKERS:
            if stop.is_set():
                break
            if time.monotonic() >= deadline:
                result.errors.append("batch:timeout")
                break
            try:
                items = yf.Ticker(ticker, session=session).get_news(count=10)
                if not isinstance(items, list):
                    result.errors.append(f"{ticker}:invalid_response")
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        result.errors.append(f"{ticker}:invalid_item")
                    elif not item.get("ad"):
                        result.articles.append(_yahoo_article(item, category))
            except Exception as exc:
                result.errors.append(f"{ticker}:{_error_code(exc)}")
    return result


def _yfinance_fetcher() -> Callable[[], Awaitable[ProviderResult]]:
    lock = threading.Lock()

    async def fetch() -> ProviderResult:
        stop = threading.Event()

        def run() -> ProviderResult:
            # Cancelling an await cannot stop a running thread. Do not start a
            # second Yahoo batch while a cancelled batch is still unwinding.
            if not lock.acquire(blocking=False):
                return ProviderResult([], ["previous_request_running"])
            try:
                return _fetch_yfinance_sync(stop)
            except Exception as exc:
                return ProviderResult([], [_error_code(exc)])
            finally:
                lock.release()

        try:
            return await asyncio.to_thread(run)
        finally:
            stop.set()

    return fetch


async def _disabled_fetch() -> ProviderResult:
    return ProviderResult([], ["disabled"])


def build_providers(
    client: httpx.AsyncClient, environ: Mapping[str, str] | None = None
) -> list[NewsProvider]:
    """Build provider configuration without requesting news or reading .env files.

    All HTTP sources require explicit credentials. The optional yfinance extra
    enables Yahoo unless NEWS_YFINANCE_ENABLED is false. CryptoPanic's plan
    segment defaults to growth; its key must have access to the selected plan.
    """
    env = os.environ if environ is None else environ
    providers = []
    specifications = (
        ("Finnhub", _fetch_finnhub, ("FINNHUB_KEY",)),
        ("CryptoPanic", _fetch_cryptopanic, ("CRYPTOPANIC_KEY",)),
        ("CoinDesk", _fetch_coindesk, ("COINDESK_KEY",)),
        ("Messari", _fetch_messari, ("MESSARI_KEY",)),
        ("Alpaca", _fetch_alpaca, ("ALPACA_KEY", "ALPACA_SECRET")),
        ("Marketaux", _fetch_marketaux, ("MARKETAUX_KEY",)),
        ("NewsAPI", _fetch_newsapi, ("NEWSAPI_KEY",)),
    )
    for name, fetch, variables in specifications:
        values = [env.get(variable, "").strip() for variable in variables]
        missing = [variable for variable, value in zip(variables, values) if not value]
        reason = f"missing_config:{','.join(missing)}" if missing else None
        if name == "CryptoPanic":
            plan = env.get("CRYPTOPANIC_PLAN", "growth").strip().lower()
            if plan not in {"developer", "growth", "enterprise"}:
                reason = "invalid_config:CRYPTOPANIC_PLAN"
            values.append(plan)
        providers.append(NewsProvider(
            name=name,
            fetch=partial(fetch, client, *values) if reason is None else _disabled_fetch,
            enabled=reason is None,
            disabled_reason=reason,
        ))

    yahoo_enabled = env.get("NEWS_YFINANCE_ENABLED", "true").strip().lower()
    reason = None
    if yahoo_enabled in {"0", "false", "no", "off"}:
        reason = "disabled_by_config"
    elif yahoo_enabled not in {"1", "true", "yes", "on"}:
        reason = "invalid_config:NEWS_YFINANCE_ENABLED"
    elif importlib.util.find_spec("yfinance") is None:
        reason = "missing_dependency:yfinance"
    providers.append(NewsProvider(
        name="yFinance",
        fetch=_yfinance_fetcher() if reason is None else _disabled_fetch,
        enabled=reason is None,
        disabled_reason=reason,
    ))
    return providers
