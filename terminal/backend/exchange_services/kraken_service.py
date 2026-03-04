import asyncio
from typing import List, Optional, Tuple

from exchange_services.exchange import ExchangeService
from models import (
    PlaceOrderRequest,
    OrderResponse,
    TradeResponse,
    AvailableCashResponse,
    AvailablePositionResponse,
    AllBalancesResponse,
    AllPositionsResponse,
)


class KrakenService(ExchangeService):
    """Kraken exchange service. Inherits from ExchangeService."""

    def __init__(self, base_url: str = "https://api.kraken.com", simulated: bool = False):
        super().__init__(base_url)
        self.simulated = simulated

    async def place_order(
        self, request: PlaceOrderRequest
    ) -> Tuple[Optional[OrderResponse], Optional[str]]:
        raise NotImplementedError

    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        raise NotImplementedError

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        raise NotImplementedError

    async def get_trades(self, pair: Optional[str] = None, limit: int = 100) -> List[TradeResponse]:
        raise NotImplementedError

    async def get_available_cash(self, pair: str) -> AvailableCashResponse:
        raise NotImplementedError

    async def get_available_positions(self, pair: str) -> AvailablePositionResponse:
        raise NotImplementedError

    async def get_all_balances(self) -> AllBalancesResponse:
        raise NotImplementedError

    async def get_all_positions(self) -> AllPositionsResponse:
        raise NotImplementedError

    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        raise NotImplementedError

    async def stop_order_stream(self) -> None:
        raise NotImplementedError
