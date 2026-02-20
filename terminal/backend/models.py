from pydantic import BaseModel
from typing import Literal


class Order(BaseModel):
    symbol: str
    exchange: str
    quantity: int
    price: float | None = None
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"]



class OrdersRequest(BaseModel):
    exchange: str

