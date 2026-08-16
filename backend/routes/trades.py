from typing import List

from fastapi import APIRouter, Query, Request

from models import TradeResponse

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/{exchange}", response_model=List[TradeResponse])
async def get_trades(
    request: Request,
    exchange: str,
    pair: str = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    """Fetch recent fill history for a specific exchange."""
    service = request.app.state.service_container.get_service(exchange)
    return await service.get_trades(pair=pair, limit=limit)
