import logging

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

    @property
    def ai_available(self) -> bool:
        return self.claude is not None

    @property
    def events(self) -> list[NewsEvent]:
        return [event.model_copy(deep=True) for event in self._events]

    async def process(self, articles: list[NewsArticle]) -> list[NewsEvent]:
        events = group_articles(articles)
        for index, event in enumerate(events):
            if index < self.max_insights:
                event.insight = await self._insight_for(event)
            event.insight_status = "validated" if event.insight else "unavailable"
        self._events = events
        return self.events

    async def aclose(self) -> None:
        if self.claude:
            await self.claude.aclose()

    async def _insight_for(self, event: NewsEvent) -> Insight | None:
        model = self.claude.model if self.claude else "unconfigured"
        key = ":".join([event.content_hash, model, PROMPT_VERSION, SCHEMA_VERSION])
        if key in self._cache:
            return self._cache[key]
        if not self.claude:
            return None
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
