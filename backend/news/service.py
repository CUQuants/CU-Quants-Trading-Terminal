"""Scheduled news refreshes, bounded process-local cache, and provider health."""

import asyncio
import logging
import math
import os
from contextlib import suppress
from datetime import datetime, timedelta, timezone

import httpx

from models import NewsArticle, NewsProviderStatus, NewsStatusResponse
from news.normalization import deduplicate_articles, match_article, normalize_article
from news.providers import NewsProvider, ProviderResult, build_providers

logger = logging.getLogger(__name__)

_DEFAULT_REFRESH_INTERVAL = 300.0
_MIN_REFRESH_INTERVAL = 30.0


def _refresh_interval_from_env(cache_ttl: float) -> float:
    """Read NEWS_REFRESH_SECONDS; fall back to the default rather than fail startup."""
    raw = os.environ.get("NEWS_REFRESH_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_REFRESH_INTERVAL
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    # Below the minimum burns provider quotas; at or above the TTL the cache
    # empties before the next refresh can repopulate it.
    if not math.isfinite(value) or not _MIN_REFRESH_INTERVAL <= value < cache_ttl:
        logger.warning(
            "Ignoring NEWS_REFRESH_SECONDS=%r (must be >= %g and < %g); using %g",
            raw, _MIN_REFRESH_INTERVAL, cache_ttl, _DEFAULT_REFRESH_INTERVAL,
        )
        return _DEFAULT_REFRESH_INTERVAL
    return value


class NewsService:
    """One service per app lifespan; requests never fetch from upstream providers."""

    def __init__(
        self,
        providers: list[NewsProvider] | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        refresh_interval: float | None = None,
        provider_timeout: float = 30,
        cache_ttl: float = 3600,
        max_articles: int = 500,
    ) -> None:
        if refresh_interval is None:
            refresh_interval = _refresh_interval_from_env(cache_ttl)
        if min(refresh_interval, provider_timeout, cache_ttl, max_articles) <= 0:
            raise ValueError("News intervals and cache limits must be positive")
        self._owns_client = providers is None and client is None
        self._client = client
        if providers is None:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=8.0)
            providers = build_providers(self._client)
        if len({provider.name for provider in providers}) != len(providers):
            raise ValueError("News provider names must be unique")
        self._providers = providers
        self._refresh_interval = refresh_interval
        self._provider_timeout = provider_timeout
        self._cache_ttl = cache_ttl
        self._max_articles = max_articles
        self._statuses = {
            provider.name: NewsProviderStatus(
                name=provider.name,
                enabled=provider.enabled,
                state="pending" if provider.enabled else "disabled",
                disabled_reason=provider.disabled_reason,
            )
            for provider in providers
        }
        self._snapshots: dict[str, tuple[datetime, list[NewsArticle]]] = {}
        self._cache: list[NewsArticle] = []
        self._cache_expires_at: datetime | None = None
        self._last_refresh: datetime | None = None
        self._last_success: datetime | None = None
        self._next_refresh: datetime | None = None
        self._refresh_lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start one background loop without delaying application startup."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._refresh_loop(), name="news-refresh")

    async def _refresh_loop(self) -> None:
        try:
            while True:
                started = asyncio.get_running_loop().time()
                self._next_refresh = datetime.now(timezone.utc) + timedelta(
                    seconds=self._refresh_interval
                )
                try:
                    await self.refresh()
                except Exception as exc:
                    # Exception messages may contain credential-bearing request URLs.
                    logger.error("News refresh failed (%s)", type(exc).__name__)
                delay = max(
                    0, self._refresh_interval - (asyncio.get_running_loop().time() - started)
                )
                await asyncio.sleep(delay)
        finally:
            self._next_refresh = None

    async def _fetch_provider(
        self, provider: NewsProvider
    ) -> tuple[str, ProviderResult, datetime]:
        attempted_at = datetime.now(timezone.utc)
        try:
            result = await asyncio.wait_for(provider.fetch(), self._provider_timeout)
        except httpx.HTTPStatusError as exc:
            result = ProviderResult([], [f"HTTP {exc.response.status_code}"])
        except Exception as exc:
            result = ProviderResult([], [type(exc).__name__])
        return provider.name, result, attempted_at

    async def refresh(self) -> None:
        """Refresh concurrently; failed sources keep their last usable snapshot."""
        if self._refresh_lock.locked():
            return
        async with self._refresh_lock:
            snapshots = {}
            statuses = {name: value.model_copy(deep=True) for name, value in self._statuses.items()}
            tasks = [
                asyncio.create_task(self._fetch_provider(provider))
                for provider in self._providers
                if provider.enabled
            ]
            usable_response = False
            try:
                for task in asyncio.as_completed(tasks):
                    name, result, attempted_at = await task
                    status = statuses[name]
                    status.last_attempt = attempted_at
                    articles = []
                    rejected = 0
                    for raw in result.articles:
                        article = normalize_article(raw) if isinstance(raw, dict) else None
                        if article is None:
                            rejected += 1
                        else:
                            articles.append(article)
                    errors = list(result.errors)
                    if rejected:
                        errors.append(f"Invalid articles: {rejected}")
                    completed_at = datetime.now(timezone.utc)
                    previous = self._snapshots.get(name)
                    if errors:
                        status.state = "degraded" if articles else "error"
                        status.last_error = "; ".join(errors)
                        status.consecutive_failures += 1
                        status.total_failures += 1
                        logger.warning("News provider %s failed: %s", name, status.last_error)
                        if previous is not None:
                            snapshots[name] = previous
                    else:
                        status.state = "ok"
                        status.last_error = None
                        status.consecutive_failures = 0
                    if articles or not errors:
                        usable_response = True
                        status.last_success = completed_at
                        # A degraded batch must not extend the lifetime of old articles.
                        # Retain the old snapshot age until a complete response arrives.
                        fetched_at = completed_at
                        if errors and previous is not None:
                            fetched_at, previous_articles = previous
                            if (completed_at - fetched_at).total_seconds() < self._cache_ttl:
                                articles.extend(previous_articles)
                            else:
                                fetched_at = completed_at
                        articles = self._sort_articles(deduplicate_articles(articles))
                        snapshots[name] = (fetched_at, articles[: self._max_articles])
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            # Publish all changes together so readers see a complete refresh snapshot.
            self._snapshots = snapshots
            self._statuses = statuses
            self._last_refresh = datetime.now(timezone.utc)
            if usable_response:
                self._last_success = self._last_refresh
            self._rebuild_cache(self._last_refresh)

    @staticmethod
    def _sort_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
        return sorted(
            articles,
            key=lambda article: article.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    def _rebuild_cache(self, now: datetime) -> None:
        self._snapshots = {
            name: snapshot
            for name, snapshot in self._snapshots.items()
            if (now - snapshot[0]).total_seconds() < self._cache_ttl
        }
        articles = [article for _, batch in self._snapshots.values() for article in batch]
        self._cache = self._sort_articles(deduplicate_articles(articles))[: self._max_articles]
        self._cache_expires_at = min(
            (fetched_at + timedelta(seconds=self._cache_ttl) for fetched_at, _ in self._snapshots.values()),
            default=None,
        )

    def _expire_cache(self, now: datetime) -> None:
        if self._cache_expires_at is not None and now >= self._cache_expires_at:
            self._rebuild_cache(now)

    def get_articles(
        self,
        *,
        pairs: list[str] | None = None,
        assets: list[str] | None = None,
        category: str | None = None,
        source: str | None = None,
        query: str | None = None,
        matched_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NewsArticle]:
        """Filter a cache snapshot and add request-specific matching on copies."""
        self._expire_cache(datetime.now(timezone.utc))
        result = []
        for article in self._cache:
            if category and category != "All" and article.category != category:
                continue
            if source and source.casefold() not in (
                article.source.casefold(), article.source.split("/")[0].casefold()
            ):
                continue
            if query and query.casefold() not in f"{article.title} {article.summary}".casefold():
                continue
            matched = match_article(article, pairs or [], assets or [])
            if not matched_only or matched.matched:
                result.append(matched)
        return result[offset: offset + limit]

    def get_status(self) -> NewsStatusResponse:
        now = datetime.now(timezone.utc)
        self._expire_cache(now)
        providers = []
        for name, original in self._statuses.items():
            status = original.model_copy(deep=True)
            snapshot = self._snapshots.get(name)
            status.article_count = len(snapshot[1]) if snapshot else 0
            status.stale = (
                snapshot is None
                or status.state != "ok"
                or (now - snapshot[0]).total_seconds() >= self._refresh_interval * 2
            )
            providers.append(status)
        return NewsStatusResponse(
            refresh_interval_seconds=self._refresh_interval,
            refreshing=self._refresh_lock.locked(),
            last_refresh=self._last_refresh,
            last_success=self._last_success,
            next_refresh=self._next_refresh,
            article_count=len(self._cache),
            stale=not any(provider.enabled and not provider.stale for provider in providers),
            providers=providers,
        )

    async def aclose(self) -> None:
        """Cancel in-flight refreshes before closing the owned HTTP connection pool."""
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._owns_client and self._client is not None:
            await self._client.aclose()
