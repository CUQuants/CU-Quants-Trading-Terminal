from fastapi import APIRouter, Query, Request

from models import TradesPage

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/{exchange}", response_model=TradesPage)
async def get_trades(
    request: Request,
    exchange: str,
    pair: str = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Fetch one page of fill history for a specific exchange, newest first.

    Pass the returned `next_offset` back as `offset` to get older fills. It is
    None when there are no more (or the exchange doesn't page).
    """
    service = request.app.state.service_container.get_service(exchange)
    return await service.get_trades_page(pair=pair, limit=limit, offset=offset)
