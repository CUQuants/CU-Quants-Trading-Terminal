from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from news.grouping import apply_pairs, source_id, to_api_article
from news.models import (
    AiStatus,
    Article,
    FilterOption,
    NewsEvent,
    NewsFeed,
    NewsStatus,
    SourceStatus,
)
from news.processor import NewsEventProcessor
from news.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])

_CATEGORIES = (
    FilterOption(id="Crypto", label="Crypto"),
    FilterOption(id="Trad-Fi", label="Traditional Finance"),
    FilterOption(id="FX/Macro", label="FX / Macro"),
    FilterOption(id="Geo-Politics", label="Geopolitics"),
)
_TIMEFRAMES = {"1h": 1, "24h": 24, "7d": 24 * 7}
NewsCategory = Literal["Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics"]


def _news(request: Request) -> NewsService:
    service = getattr(request.app.state, "news_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="News service is not running.")
    return service


def _events(request: Request) -> NewsEventProcessor:
    processor = getattr(request.app.state, "news_event_processor", None)
    if processor is None:
        raise HTTPException(status_code=503, detail="News events are not running.")
    return processor


def _feed_metadata(service: NewsService) -> tuple[datetime | None, float]:
    status = service.get_status()
    return status.last_success, max(1, status.refresh_interval_seconds * 2)


def _matches_time(value: datetime, timeframe: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_TIMEFRAMES[timeframe])
    return value >= cutoff


@router.get("", response_model=NewsFeed[Article])
async def get_news(
    request: Request,
    category: NewsCategory | None = None,
    source: str | None = Query(default=None, max_length=100),
    timeframe: Literal["1h", "24h", "7d"] = "24h",
    pair: list[str] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    service = _news(request)
    items = []
    for raw in service.get_articles():
        article = to_api_article(raw, pair)
        if article is None or not _matches_time(article.published_at, timeframe):
            continue
        if category and article.category != category:
            continue
        if source and article.source_id != source:
            continue
        if pair and not article.matched_pairs:
            continue
        items.append(article)
    last_success, stale_after = _feed_metadata(service)
    return NewsFeed(
        items=items[:limit],
        total=len(items),
        last_successful_refresh_at=last_success,
        stale_after_seconds=stale_after,
    )


@router.get("/events", response_model=NewsFeed[NewsEvent])
async def get_news_events(
    request: Request,
    category: NewsCategory | None = None,
    source: str | None = Query(default=None, max_length=100),
    timeframe: Literal["1h", "24h", "7d"] = "24h",
    pair: list[str] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    service = _news(request)
    events = []
    for original in _events(request).events:
        event = apply_pairs(original, pair or [])
        if not _matches_time(event.updated_at, timeframe):
            continue
        if category and event.category != category:
            continue
        if source and not any(article.source_id == source for article in event.articles):
            continue
        if pair and not event.matched_pairs:
            continue
        events.append(event)
    last_success, stale_after = _feed_metadata(service)
    return NewsFeed(
        items=events[:limit],
        total=len(events),
        last_successful_refresh_at=last_success,
        stale_after_seconds=stale_after,
    )


@router.get("/status", response_model=NewsStatus)
async def get_news_status(request: Request):
    service = _news(request)
    processor = getattr(request.app.state, "news_event_processor", None)
    sources = []
    for provider in service.get_status().providers:
        if provider.state == "ok":
            state = "healthy"
        elif provider.state == "degraded":
            state = "degraded"
        else:
            state = "unavailable"
        sources.append(SourceStatus(
            id=source_id(provider.name),
            name=provider.name,
            status=state,
            last_successful_refresh_at=provider.last_success,
            message=provider.last_error or provider.disabled_reason,
        ))
    available = bool(processor and processor.ai_available)
    return NewsStatus(
        checked_at=datetime.now(timezone.utc),
        sources=sources,
        categories=list(_CATEGORIES),
        ai=AiStatus(
            status="available" if available else "unavailable",
            message=None if available else "Claude insights are not configured.",
        ),
    )
