from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio

import httpx

from models import PlaceOrderRequest, OrderResponse, TradeResponse


class ExchangeService(ABC):

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def _request(self, method: str, path: str, body: str = None, headers: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, f"{self.base_url}{path}", content=body, headers=headers)
            response.raise_for_status()
            return response.json()

    @abstractmethod
    async def place_order(self, request: PlaceOrderRequest) -> OrderResponse:
        pass

    @abstractmethod
    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, pair: str) -> bool:
        pass

    @abstractmethod
    async def get_trades(self, pair: Optional[str] = None, limit: int = 100) -> List[TradeResponse]:
        pass

    @abstractmethod
    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        """Start streaming order events into the provided queue."""
        pass

    @abstractmethod
    async def stop_order_stream(self) -> None:
        """Stop the order event stream and clean up resources."""
        pass