from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


def _camel_case(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.title() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class Article(ApiModel):
    id: str
    source_id: str
    source_name: str
    url: str
    headline: str
    published_at: datetime
    excerpt: str | None = None
    category: str
    matched_assets: list[str] = Field(default_factory=list)
    matched_pairs: list[str] = Field(default_factory=list)


class InsightStatement(ApiModel):
    text: str
    article_ids: list[str]


class Insight(ApiModel):
    event_id: str
    generated_at: datetime
    model: str
    factual_summary: list[InsightStatement]
    market_context: list[InsightStatement]
    what_to_watch: list[InsightStatement]
    confidence: Literal["low", "medium", "high"]
    validation_status: Literal["validated"] = "validated"
    prompt_version: str = Field(exclude=True)
    schema_version: str = Field(exclude=True)
    latency_ms: int | None = Field(default=None, exclude=True)
    input_tokens: int | None = Field(default=None, exclude=True)
    output_tokens: int | None = Field(default=None, exclude=True)


class NewsEvent(ApiModel):
    id: str
    headline: str
    category: str
    first_reported_at: datetime
    updated_at: datetime
    matched_assets: list[str]
    matched_pairs: list[str]
    source_count: int
    articles: list[Article]
    insight_status: Literal["pending", "validated", "unavailable"] = "pending"
    insight: Insight | None = None
    content_hash: str = Field(exclude=True)


Item = TypeVar("Item")


class NewsFeed(ApiModel, Generic[Item]):
    items: list[Item]
    total: int
    last_successful_refresh_at: datetime | None
    stale_after_seconds: float


class SourceStatus(ApiModel):
    id: str
    name: str
    status: Literal["healthy", "degraded", "unavailable"]
    last_successful_refresh_at: datetime | None
    message: str | None = None


class FilterOption(ApiModel):
    id: str
    label: str


class AiStatus(ApiModel):
    status: Literal["available", "unavailable"]
    message: str | None = None


class NewsStatus(ApiModel):
    checked_at: datetime
    sources: list[SourceStatus]
    categories: list[FilterOption]
    ai: AiStatus
