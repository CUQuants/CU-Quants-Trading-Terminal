from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


InsightStatus = Literal[
    "pending",
    "ready",
    "insufficient_evidence",
    "unavailable",
    "rejected",
]


class Article(BaseModel):
    id: str
    canonical_url: str
    source: str
    title: str
    excerpt: str = ""
    published_at_utc: datetime
    ingested_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    category: str = "General"
    assets: list[str] = Field(default_factory=list)
    matched_pairs: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class Insight(BaseModel):
    event_id: str
    model_version: str
    status: InsightStatus
    factual_summary: str = ""
    market_context: str = ""
    affected_assets: list[str] = Field(default_factory=list)
    what_to_watch: list[str] = Field(default_factory=list)
    time_horizon: Literal["immediate", "intraday", "multi-day", "unclear"] = "unclear"
    impact_level: Literal["low", "medium", "high", "unclear"] = "unclear"
    confidence: Literal["low", "medium", "high"] = "low"
    evidence_article_ids: list[str] = Field(default_factory=list)
    generated_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    prompt_version: str
    schema_version: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class NewsEvent(BaseModel):
    id: str
    representative_article_id: str
    related_article_ids: list[str]
    headline: str
    category: str
    assets: list[str]
    matched_pairs: list[str]
    first_published_at_utc: datetime
    last_updated_at_utc: datetime
    articles: list[Article]
    content_hash: str = Field(exclude=True)
    insight: Insight | None = None
