from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class Order(BaseModel):
    symbol: str
    exchange: str
    quantity: int
    price: float | None = None
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"]


class OrderResponse(BaseModel):
    id: str
    symbol: str
    exchange: str
    quantity: int
    price: float | None = None
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"]
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

class OrdersRequest(BaseModel):
    exchange: str

