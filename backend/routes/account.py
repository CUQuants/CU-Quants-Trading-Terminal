from typing import Union

from fastapi import APIRouter, Query, Request

from models import (
    AvailableCashResponse,
    AvailablePositionResponse,
    AllBalancesResponse,
    AllPositionsResponse,
)

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


@router.get("/positions/{exchange}")
async def get_positions(
    request: Request,
    exchange: str,
    pair: str | None = Query(None, description="Trading pair (e.g. BTC/USD). Omit for all positions."),
) -> Union[AvailablePositionResponse, AllPositionsResponse]:
    """Fetch position for a pair, or all positions if pair is omitted."""
    service = request.app.state.service_container.get_service(exchange)
    if pair:
        return await service.get_available_positions(pair=pair)
    return await service.get_all_positions()


@router.get("/balances/{exchange}", response_model=AllBalancesResponse)
async def get_all_balances(request: Request, exchange: str):
    """Fetch full account balance (all currencies) for an exchange."""
    service = request.app.state.service_container.get_service(exchange)
    return await service.get_all_balances()
