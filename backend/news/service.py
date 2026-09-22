import logging
from datetime import datetime, timezone

from .claude import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ClaudeClient,
    ClaudeRejectedError,
)
from .grouping import group_articles
from .models import Article, Insight, NewsEvent

logger = logging.getLogger(__name__)


class NewsEventProcessor:
    def __init__(self, claude: ClaudeClient | None = None):
        self.claude = claude
        self._cache: dict[str, Insight] = {}
        self._events: list[NewsEvent] = []

    @property
    def events(self) -> list[NewsEvent]:
        return list(self._events)

    async def process(self, articles: list[Article]) -> list[NewsEvent]:
        events = group_articles(articles)
        for event in events:
            event.insight = await self._insight_for(event)
        self._events = events
        return self.events

    async def aclose(self) -> None:
        if self.claude:
            await self.claude.aclose()

    async def _insight_for(self, event: NewsEvent) -> Insight:
        model = self.claude.model if self.claude else "unconfigured"
        cache_key = ":".join(
            [event.content_hash, model, PROMPT_VERSION, SCHEMA_VERSION]
        )
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.claude:
            return self._fallback(event, "unavailable", model)

        try:
            insight = await self.claude.create_insight(event)
        except ClaudeRejectedError:
            logger.warning("Rejected Claude output for event %s", event.id)
            insight = self._fallback(event, "rejected", model)
            self._cache[cache_key] = insight
            return insight
        except Exception:
            logger.exception("Claude enrichment failed for event %s", event.id)
            return self._fallback(event, "unavailable", model)

        self._cache[cache_key] = insight
        logger.info(
            "Created news insight event=%s model=%s latency_ms=%s input_tokens=%s output_tokens=%s",
            event.id,
            insight.model_version,
            insight.latency_ms,
            insight.input_tokens,
            insight.output_tokens,
        )
        return insight

    @staticmethod
    def _fallback(event: NewsEvent, status: str, model: str) -> Insight:
        return Insight(
            event_id=event.id,
            model_version=model,
            status=status,
            generated_at_utc=datetime.now(timezone.utc),
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
        )
