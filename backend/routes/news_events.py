from fastapi import APIRouter, HTTPException, Query, Request

from news.models import NewsEvent

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/events", response_model=list[NewsEvent])
async def get_news_events(
    request: Request,
    pair: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
):
    processor = getattr(request.app.state, "news_event_processor", None)
    if processor is None:
        raise HTTPException(
            status_code=503,
            detail="News event processor is not configured.",
        )

    events = processor.events
    if pair:
        normalized_pair = pair.upper()
        events = [event for event in events if normalized_pair in event.matched_pairs]
    return events[:limit]
