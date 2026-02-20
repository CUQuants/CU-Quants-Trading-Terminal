from abc import ABC, abstractmethod
from models import Order
from typing import List


class ExchangeService(ABC):

    def __init__(self, base_url: str):
        self.base_url = base_url

    @abstractmethod
    def _get_headers(self, method: str, request_path: str, body: str = "") -> dict:
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> Order:
        pass

    @abstractmethod
    async def get_orders(self) -> List[Order]:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
