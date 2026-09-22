from pydantic import BaseModel
from typing import Any, Literal, Optional, List


class PlaceOrderRequest(BaseModel):
    pair: str
    side: Literal["buy", "sell"]
    type: Literal["limit", "market", "iceberg"]
    visible_size: Optional[float] = None
    price: Optional[float] = None
    size: float


class OrderResponse(BaseModel):
    id: str
    pair: str
    exchange: str
    side: Literal["buy", "sell"]
    type: Literal["limit", "market", "iceberg"]
    price: Optional[float] = None
    visible_size: Optional[float] = None
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


class AvailableCashResponse(BaseModel):
    """Available balance for the quote currency (e.g. USDT) of a pair."""
    exchange: str
    currency: str
    available: float
    frozen: float
    total: float


class AvailablePositionResponse(BaseModel):
    """Available balance for the base currency (e.g. BTC) of a pair."""
    exchange: str
    pair: str
    base_currency: str
    available: float
    frozen: float
    total: float


# --- Account page: all balances and positions ---

class BalanceEntry(BaseModel):
    """Single currency balance."""
    currency: str
    available: float
    frozen: float
    total: float


class AllBalancesResponse(BaseModel):
    """Full account balance for an exchange."""
    exchange: str
    currencies: List[BalanceEntry]


class PositionEntry(BaseModel):
    """Single position (non-cash, non-zero holding)."""
    currency: str
    available: float
    frozen: float
    total: float


class AllPositionsResponse(BaseModel):
    """All positions for an exchange (non-zero, non-cash)."""
    exchange: str
    positions: List[PositionEntry]


# --- Reporting (audit log) ---
# Field shapes mirror proxy_client.ReportingClient's docstrings, confirmed
# against trading-gateway/proxy_admin/proxy_admin/reporting/db.py's
# UnresolvedOrder / LogHealth / AuthFailureSummary / LogRow dataclasses.

class LogHealthResponse(BaseModel):
    """Partition runway, clock skew, default-partition drift."""
    months_of_runway: int
    default_partition_rows: int
    unprotected_partitions: int
    rows_last_24h: int
    newest_row: Optional[str] = None
    max_clock_skew_sec: Optional[float] = None


class UnresolvedOrderResponse(BaseModel):
    """An order forwarded to an exchange whose outcome was never recorded."""
    request_id: str
    timestamp: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    system_name: Optional[str] = None
    exchange: Optional[str] = None
    action: str
    source_ip: Optional[str] = None
    unresolved_for: str


class AuthFailureResponse(BaseModel):
    """Authentication failures in the last 7 days, by key and origin."""
    api_key_id: Optional[str] = None
    source_ip: Optional[str] = None
    failures: int
    latest: str


class LogEntryResponse(BaseModel):
    """One row of request_log."""
    request_id: str
    action: str
    response_status: Optional[str] = None
    timestamp: str
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    system_name: Optional[str] = None
    exchange: Optional[str] = None
    request_payload: Optional[Any] = None
    response_summary: Optional[Any] = None
    latency_ms: Optional[int] = None
    source_ip: Optional[str] = None
    order_id: Optional[str] = None
    http_status: Optional[int] = None
    error_code: Optional[str] = None
    api_key_id: Optional[str] = None


class LogPageResponse(BaseModel):
    """One filtered/paginated page of request_log."""
    logs: List[LogEntryResponse]
    next_cursor: Optional[str] = None