import logging
import asyncio
from contextlib import suppress

from models import NewsArticle
from news.claude import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ClaudeClient,
    ClaudeRejectedError,
)
from news.grouping import group_articles
from news.models import Insight, NewsEvent

logger = logging.getLogger(__name__)


class NewsEventProcessor:
    def __init__(self, claude: ClaudeClient | None = None, max_insights: int = 25):
        self.claude = claude
        self.max_insights = max_insights
        self._cache: dict[str, Insight | None] = {}
        self._events: list[NewsEvent] = []
        self._task: asyncio.Task | None = None

    @property
    def ai_available(self) -> bool:
        return self.claude is not None

    @property
    def events(self) -> list[NewsEvent]:
        return [event.model_copy(deep=True) for event in self._events]

    async def process(self, articles: list[NewsArticle]) -> list[NewsEvent]:
        if self._task is not None:
            self._task.cancel()
        events = group_articles(articles)
        for index, event in enumerate(events):
            if self.claude and index < self.max_insights:
                key = self._cache_key(event)
                if key in self._cache:
                    event.insight = self._cache[key]
                    event.insight_status = "validated" if event.insight else "unavailable"
            else:
                event.insight_status = "unavailable"
        self._events = events
        pending = [event for event in events if event.insight_status == "pending"]
        if pending:
            self._task = asyncio.create_task(self._enrich(pending), name="news-insights")
        return self.events

    async def aclose(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        if self.claude:
            await self.claude.aclose()

    def _cache_key(self, event: NewsEvent) -> str:
        return ":".join([event.content_hash, self.claude.model, PROMPT_VERSION, SCHEMA_VERSION])

    async def _enrich(self, events: list[NewsEvent]) -> None:
        limit = asyncio.Semaphore(3)

        async def enrich(event: NewsEvent) -> None:
            async with limit:
                event.insight = await self._insight_for(event)
                event.insight_status = "validated" if event.insight else "unavailable"

        await asyncio.gather(*(enrich(event) for event in events))

    async def _insight_for(self, event: NewsEvent) -> Insight | None:
        key = self._cache_key(event)
        if key in self._cache:
            return self._cache[key]
        try:
            insight = await self.claude.create_insight(event)
        except ClaudeRejectedError:
            logger.warning("Rejected Claude output for event %s", event.id)
            self._cache[key] = None
            return None
        except Exception:
            logger.exception("Claude enrichment failed for event %s", event.id)
            return None
        self._cache[key] = insight
        if insight:
            logger.info(
                "Created news insight event=%s model=%s latency_ms=%s tokens=%s/%s",
                event.id,
                insight.model,
                insight.latency_ms,
                insight.input_tokens,
                insight.output_tokens,
            )
        return insight
