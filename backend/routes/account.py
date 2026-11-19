from typing import Union

from fastapi import APIRouter, Depends, Query

from models import (
    AvailableCashResponse,
    AvailablePositionResponse,
    AllBalancesResponse,
    AllPositionsResponse,
)

from auth import current_container
from exchange_services.service_container import ServiceContainer

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/cash/{exchange}", response_model=AvailableCashResponse)
async def get_available_cash(
    exchange: str,
    pair: str = Query(..., description="Trading pair (e.g. BTC/USD)"),
    container: ServiceContainer = Depends(current_container),
):
    """Fetch available cash (quote currency balance) for a pair."""
    service = container.get_service(exchange)
    return await service.get_available_cash(pair=pair)


@router.get("/positions/{exchange}")
async def get_positions(
    exchange: str,
    pair: str | None = Query(None, description="Trading pair (e.g. BTC/USD). Omit for all positions."),
    container: ServiceContainer = Depends(current_container),
) -> Union[AvailablePositionResponse, AllPositionsResponse]:
    """Fetch position for a pair, or all positions if pair is omitted."""
    service = container.get_service(exchange)
    if pair:
        return await service.get_available_positions(pair=pair)
    return await service.get_all_positions()


@router.get("/balances/{exchange}", response_model=AllBalancesResponse)
async def get_all_balances(exchange: str, container: ServiceContainer = Depends(current_container)):
    """Fetch full account balance (all currencies) for an exchange."""
    service = container.get_service(exchange)
    return await service.get_all_balances()
