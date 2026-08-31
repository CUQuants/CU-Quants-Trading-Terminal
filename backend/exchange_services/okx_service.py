import asyncio
import logging
from typing import Dict, List, Optional

from proxy_client import new_idempotency_key
from proxy_client.errors import ExchangeError, ProxyError

from exchange_services.exchange import ExchangeService
from exchange_services.proxy_session import ProxySession
from exchange_services.okx_order_stream import OkxOrderEventStream
from models import (
    PlaceOrderRequest,
    OrderResponse,
    TradeResponse,
    AvailableCashResponse,
    AvailablePositionResponse,
    AllBalancesResponse,
    AllPositionsResponse,
    BalanceEntry,
    PositionEntry,
)

logger = logging.getLogger(__name__)


class OkxService(ExchangeService):
    """OKX spot service, routed entirely through the CU Quants Proxy.

    The terminal holds no OKX credentials — every call here is
    `self._proxy.call("okx", <action>, <payload>)`, where the Proxy signs
    with the club's vaulted key, enforces the §4.2 allowlist and the
    spot-only rule, and logs the request. Payloads are OKX's own field
    names (`instId`, `tdMode`, `sz`, ...) and responses come back as OKX's
    own body (`{"code": "0", "data": [...]}`), so the parsing below is
    unchanged from when this service signed its own requests.

    Simulated vs. live is a property of the gateway `self._proxy` points at
    (`OKX_SIMULATED` there), not a setting on this class.
    """

    def __init__(self, proxy: ProxySession):
        super().__init__()
        self._proxy = proxy
        self._order_stream: OkxOrderEventStream | None = None

    # ------------------------------------------------------------------
    # Pair normalization
    # ------------------------------------------------------------------

    def _to_native_pair(self, pair: str) -> str:
        """BTC/USD -> BTC-USDT"""
        base, quote = pair.split("/")
        if quote == "USD":
            quote = "USDT"
        return f"{base}-{quote}"

    def _from_native_pair(self, native_pair: str) -> str:
        """BTC-USDT -> BTC/USD"""
        base, quote = native_pair.split("-")
        if quote == "USDT":
            quote = "USD"
        return f"{base}/{quote}"

    def _get_quote_ccy(self, pair: str) -> str:
        """BTC/USD -> USDT (OKX uses USDT for USD pairs)."""
        _, quote = pair.split("/")
        return "USDT" if quote == "USD" else quote

    def _get_base_ccy(self, pair: str) -> str:
        """BTC/USD -> BTC."""
        base, _ = pair.split("/")
        return base

    # ------------------------------------------------------------------
    # REST: orders
    # ------------------------------------------------------------------

    @staticmethod
    def _order_error_message(data: dict) -> str:
        """Pull a human error string out of an OKX order-rejection body.

        `data` is OKX's own `{"code", "msg", "data": [{"sCode", "sMsg"}]}`
        — via `ExchangeError.detail["body"]` when the Proxy relays a
        rejection.
        """
        err_msg = (data.get("msg") or "").strip()
        details = data.get("data") or []
        if details and isinstance(details[0], dict):
            d0 = details[0]
            s_msg = (d0.get("sMsg") or "").strip()
            s_code = d0.get("sCode", "")
            if s_msg:
                err_msg = s_msg
            elif s_code:
                err_msg = err_msg or f"Order failed (sCode={s_code})"
        if not err_msg:
            code = data.get("code", "")
            err_msg = f"Order failed (code={code})" if code else "Order failed"
            logger.warning("OKX order rejected, could not parse error: %s", data)
        return err_msg

    async def place_order(
        self, request: PlaceOrderRequest
    ) -> tuple[Optional[OrderResponse], Optional[str]]:
        payload = {
            "instId": self._to_native_pair(request.pair),
            "tdMode": "cash",
            "side": request.side,
            "ordType": request.type,
            "sz": str(request.size),
        }
        if request.type == "limit" and request.price is not None:
            payload["px"] = str(request.price)

        try:
            data = await self._proxy.call(
                "okx", "place_order", payload,
                idempotency_key=new_idempotency_key(),
            )
        except ExchangeError as e:
            body = (e.detail or {}).get("body") or {}
            return (None, self._order_error_message(body))
        except ProxyError as e:
            return (None, str(e))

        order_id = data["data"][0]["ordId"]
        order = OrderResponse(
            id=order_id,
            pair=request.pair,
            exchange="okx",
            side=request.side,
            type=request.type,
            price=request.price,
            size=request.size,
            status="live",
        )
        return (order, None)

    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        payload: dict = {"instType": "SPOT"}
        if pair:
            payload["instId"] = self._to_native_pair(pair)

        data = await self._proxy.call("okx", "get_pending_orders", payload)

        orders: List[OrderResponse] = []
        for item in data.get("data", []):
            orders.append(OrderResponse(
                id=item["ordId"],
                pair=self._from_native_pair(item["instId"]),
                exchange="okx",
                side=item["side"],
                type="limit" if item["ordType"] == "limit" else "market",
                price=float(item["px"]) if item.get("px") else None,
                size=float(item["sz"]),
                status=item["state"],
                created_at=item.get("cTime"),
            ))
        return orders

    async def get_trades(self, pair: Optional[str] = None, limit: int = 100) -> List[TradeResponse]:
        payload: dict = {"instType": "SPOT", "limit": str(limit)}
        if pair:
            payload["instId"] = self._to_native_pair(pair)

        # `get_fills` on the Proxy is OKX's /api/v5/trade/fills (last 3 days).
        # The older /fills-history window isn't on the §4.2 allowlist.
        data = await self._proxy.call("okx", "get_fills", payload)

        trades: List[TradeResponse] = []
        for item in data.get("data", []):
            exec_type = item.get("execType", "")
            trades.append(TradeResponse(
                id=item["tradeId"],
                order_id=item["ordId"],
                pair=self._from_native_pair(item["instId"]),
                exchange="okx",
                side=item["side"],
                price=float(item["fillPx"]),
                size=float(item["fillSz"]),
                fee=abs(float(item.get("fee") or 0)),
                fee_currency=item.get("feeCcy", ""),
                role="maker" if exec_type == "M" else "taker",
                timestamp=item.get("fillTime", item.get("ts", "")),
            ))
        return trades

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        payload = {
            "ordId": order_id,
            "instId": self._to_native_pair(pair),
        }
        try:
            result = await self._proxy.call(
                "okx", "cancel_order", payload,
                idempotency_key=new_idempotency_key(),
            )
        except ProxyError as e:
            logger.warning("OKX cancel_order failed: %s", e)
            return False
        return result.get("code") == "0"

    # ------------------------------------------------------------------
    # REST: account balance (cash and positions)
    # ------------------------------------------------------------------

    async def _fetch_all_balances(self) -> Dict[str, dict]:
        """Fetch full account balance from OKX (no ccy filter), filter in memory."""
        data = await self._proxy.call("okx", "get_balance", {})

        if data.get("code") != "0":
            raise Exception(f"OKX balance failed: {data}")

        result: Dict[str, dict] = {}
        for d in data.get("data", [{}])[0].get("details", []):
            ccy = d.get("ccy", "")
            result[ccy] = d
        return result

    def _balance_for_ccy(self, balances: Dict[str, dict], ccy: str) -> dict:
        """Extract balance for a currency; return zeros if missing."""
        d = balances.get(ccy)
        if not d:
            return {"availBal": "0", "frozenBal": "0", "eq": "0"}
        return d

    async def get_available_cash(self, pair: str) -> AvailableCashResponse:
        """Available balance for quote currency (USDT for USD pairs)."""
        balances = await self._fetch_all_balances()
        ccy = self._get_quote_ccy(pair)
        d = self._balance_for_ccy(balances, ccy)
        avail = float(d.get("availBal", 0) or 0)
        frozen = float(d.get("frozenBal", 0) or 0)
        total = float(d.get("eq", 0) or 0) or (avail + frozen)
        display_ccy = "USD" if ccy == "USDT" else ccy
        return AvailableCashResponse(
            exchange="okx",
            currency=display_ccy,
            available=avail,
            frozen=frozen,
            total=total,
        )

    async def get_available_positions(self, pair: str) -> AvailablePositionResponse:
        """Available balance for base currency (e.g. BTC for BTC/USD)."""
        balances = await self._fetch_all_balances()
        ccy = self._get_base_ccy(pair)
        d = self._balance_for_ccy(balances, ccy)
        avail = float(d.get("availBal", 0) or 0)
        frozen = float(d.get("frozenBal", 0) or 0)
        total = float(d.get("eq", 0) or 0) or (avail + frozen)
        return AvailablePositionResponse(
            exchange="okx",
            pair=pair,
            base_currency=ccy,
            available=avail,
            frozen=frozen,
            total=total,
        )

    # Stablecoins excluded from positions (Option C: non-zero + non-cash)
    _CASH_CCYS = frozenset({"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD"})

    async def get_all_balances(self) -> AllBalancesResponse:
        """Full account balance (all currencies)."""
        balances = await self._fetch_all_balances()
        currencies = []
        for ccy, d in balances.items():
            avail = float(d.get("availBal", 0) or 0)
            frozen = float(d.get("frozenBal", 0) or 0)
            total = float(d.get("eq", 0) or 0) or (avail + frozen)
            display_ccy = "USD" if ccy == "USDT" else ccy
            currencies.append(
                BalanceEntry(currency=display_ccy, available=avail, frozen=frozen, total=total)
            )
        return AllBalancesResponse(exchange="okx", currencies=currencies)

    async def get_all_positions(self) -> AllPositionsResponse:
        """All positions: non-zero, non-cash holdings."""
        balances = await self._fetch_all_balances()
        positions = []
        for ccy, d in balances.items():
            if ccy in self._CASH_CCYS:
                continue
            avail = float(d.get("availBal", 0) or 0)
            frozen = float(d.get("frozenBal", 0) or 0)
            total = float(d.get("eq", 0) or 0) or (avail + frozen)
            if total <= 0:
                continue
            positions.append(
                PositionEntry(currency=ccy, available=avail, frozen=frozen, total=total)
            )
        return AllPositionsResponse(exchange="okx", positions=positions)

    # ------------------------------------------------------------------
    # WS: order event stream
    # ------------------------------------------------------------------

    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        if self._order_stream is not None:
            return
        self._order_stream = OkxOrderEventStream(
            proxy=self._proxy,
            pair_normalizer=self._from_native_pair,
        )
        await self._order_stream.start(event_queue)

    async def stop_order_stream(self) -> None:
        if self._order_stream:
            await self._order_stream.stop()
            self._order_stream = None
