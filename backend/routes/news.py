from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from models import NewsArticle, NewsStatusResponse
from news.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


def _news(request: Request) -> NewsService:
    service = getattr(request.app.state, "news_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="News service is not running.")
    return service


@router.get("", response_model=List[NewsArticle])
async def get_news(
    request: Request,
    pairs: Optional[List[str]] = Query(default=None, max_length=50),
    assets: Optional[List[str]] = Query(default=None, max_length=50),
    category: Optional[Literal["All", "Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics"]] = None,
    source: Optional[str] = Query(default=None, max_length=200),
    q: Optional[str] = Query(default=None, max_length=500),
    matched_only: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Cached news, newest first; matching and filters never trigger a provider call."""
    return _news(request).get_articles(
        pairs=pairs,
        assets=assets,
        category=category,
        source=source,
        query=q,
        matched_only=matched_only,
        limit=limit,
        offset=offset,
    )


@router.get("/status", response_model=NewsStatusResponse)
async def get_news_status(request: Request):
    """Refresh timing, cache freshness, and individual provider failures."""
    return _news(request).get_status()
