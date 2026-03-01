from pydantic import BaseModel
from typing import Literal, Optional


class PlaceOrderRequest(BaseModel):
    pair: str
    side: Literal["buy", "sell"]
    type: Literal["limit", "market"]
    price: Optional[float] = None
    size: float


class OrderResponse(BaseModel):
    id: str
    pair: str
    exchange: str
    side: Literal["buy", "sell"]
    type: Literal["limit", "market"]
    price: Optional[float] = None
    size: float
    status: str
    created_at: Optional[str] = None


class TradeResponse(BaseModel):
    id: str
    order_id: str
    pair: str
    exchange: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    fee: float
    fee_currency: str
    role: Literal["maker", "taker"]
    timestamp: str


class OrderEvent(BaseModel):
    """Normalized order event pushed over WS from backend to frontend."""
    type: Literal["order_event"] = "order_event"
    exchange: str
    pair: str
    orderId: str
    status: Literal["live", "partially_filled", "filled", "canceled", "rejected"]
    side: Literal["buy", "sell"]
    price: float
    size: float
    timestamp: str


class StatusEvent(BaseModel):
    """Connection status event pushed over WS from backend to frontend."""
    type: Literal["status"] = "status"
    exchange: str
    connectionStatus: Literal["connected", "reconnecting", "disconnected"]
