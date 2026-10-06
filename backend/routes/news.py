from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from models import (
    NewsApiArticle,
    NewsApiStatus,
    NewsFeedResponse,
    NewsFilterOption,
    NewsSourceStatus,
)
from news.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


def _news(request: Request) -> NewsService:
    service = getattr(request.app.state, "news_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="News service is not running.")
    return service


@router.get("", response_model=NewsFeedResponse, response_model_exclude_unset=True)
def get_news(
    request: Request,
    pair: Optional[List[str]] = Query(default=None, max_length=50),
    pairs: Optional[List[str]] = Query(default=None, max_length=50),
    assets: Optional[List[str]] = Query(default=None, max_length=50),
    category: Optional[Literal["All", "Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics"]] = None,
    source: Optional[str] = Query(default=None, max_length=200),
    q: Optional[str] = Query(default=None, max_length=500),
    timeframe: Optional[Literal["1h", "24h", "7d"]] = None,
    matched_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Cached news, newest first; matching and filters never trigger a provider call."""
    service = _news(request)
    requested_pairs = [*(pair or []), *(pairs or [])] or None
    status = service.get_status()
    articles = service.get_articles(
        pairs=requested_pairs,
        assets=assets,
        category=category,
        source=source,
        query=q,
        timeframe=timeframe,
        matched_only=matched_only,
        limit=500,
        offset=0,
    )
    api_articles = [_to_api_article(service, article) for article in articles]
    api_articles = [article for article in api_articles if article is not None]
    return NewsFeedResponse(
        items=api_articles[offset: offset + limit],
        total=len(api_articles),
        lastSuccessfulRefreshAt=status.last_success,
        staleAfterSeconds=status.refresh_interval_seconds * 2,
    )


@router.get("/status", response_model=NewsApiStatus, response_model_exclude_unset=True)
async def get_news_status(request: Request):
    """Refresh timing, cache freshness, and individual provider failures."""
    service = _news(request)
    status = service.get_status()
    return NewsApiStatus(
        checkedAt=datetime.now(timezone.utc),
        sources=[
            NewsSourceStatus(
                id=_source_id(provider.name),
                name=provider.name,
                status=_source_state(provider.state),
                lastSuccessfulRefreshAt=provider.last_success,
                **({"message": provider.last_error or provider.disabled_reason}
                   if provider.last_error or provider.disabled_reason else {}),
            )
            for provider in status.providers
        ],
        categories=[NewsFilterOption(id=category, label=category) for category in (
            "Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics"
        )],
        ai={"status": "unavailable", "message": "Validated news events are not implemented."},
    )


def _source_id(source: str) -> str:
    return source.split("/", 1)[0].strip().casefold().replace(" ", "-")


def _source_state(state: str) -> str:
    if state == "ok":
        return "healthy"
    if state == "degraded":
        return "degraded"
    return "unavailable"


def _to_api_article(service: NewsService, article) -> NewsApiArticle | None:
    """Project only frontend-valid source reports; never invent dates or URLs."""
    if article.published_at is None or not article.url.startswith(("http://", "https://")):
        return None
    source_id = _source_id(article.source)
    return NewsApiArticle(
        id=service.article_id(article),
        sourceId=source_id,
        sourceName=article.source,
        url=article.url,
        headline=article.title,
        publishedAt=article.published_at,
        **({"excerpt": article.summary} if article.summary else {}),
        category=article.category,
        matchedAssets=article.assets,
        matchedPairs=[term for term in article.match_terms if "/" in term],
    )
