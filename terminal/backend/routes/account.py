from fastapi import APIRouter, Query, Request

from models import AvailableCashResponse, AvailablePositionResponse

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/cash/{exchange}", response_model=AvailableCashResponse)
async def get_available_cash(
    request: Request,
    exchange: str,
    pair: str = Query(..., description="Trading pair (e.g. BTC/USD)"),
):
    """Fetch available cash (quote currency balance) for a pair."""
    service = request.app.state.service_container.get_service(exchange)
    return await service.get_available_cash(pair=pair)


@router.get("/positions/{exchange}", response_model=AvailablePositionResponse)
async def get_available_positions(
    request: Request,
    exchange: str,
    pair: str = Query(..., description="Trading pair (e.g. BTC/USD)"),
):
    """Fetch available position (base currency balance) for a pair."""
    service = request.app.state.service_container.get_service(exchange)
    return await service.get_available_positions(pair=pair)
