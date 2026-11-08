import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from proxy_client import new_idempotency_key
from proxy_client.errors import ActionNotPermittedError, ExchangeError, ProxyError

from exchange_services.exchange import ExchangeService
from exchange_services.proxy_session import ProxySession
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

# Kraken uses X-prefixed crypto and Z-prefixed fiat tickers in REST responses.
# This map covers the legacy prefixed assets; newer assets (SOL, DOT, etc.)
# appear without prefixes and are passed through as-is.
_KRAKEN_ASSET_TO_STANDARD: Dict[str, str] = {
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "XLTC": "LTC",
    "XXRP": "XRP",
    "XXLM": "XLM",
    "XXMR": "XMR",
    "XZEC": "ZEC",
    "XREP": "REP",
    "XETC": "ETC",
    "XMLN": "MLN",
    "ZUSD": "USD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZCAD": "CAD",
    "ZJPY": "JPY",
    "ZAUD": "AUD",
}

_STANDARD_TO_KRAKEN_ASSET: Dict[str, str] = {v: k for k, v in _KRAKEN_ASSET_TO_STANDARD.items()}

# Legacy pair patterns used in REST responses (e.g. XXBTZUSD).
# Maps from the concatenated Kraken pair -> (base, quote) in standard form.
_KNOWN_PAIR_PREFIXES: Dict[str, Tuple[str, str]] = {
    "XXBTZUSD": ("BTC", "USD"),
    "XXBTZEUR": ("BTC", "EUR"),
    "XETHZUSD": ("ETH", "USD"),
    "XETHZEUR": ("ETH", "EUR"),
    "XETHXXBT": ("ETH", "BTC"),
    "XLTCZUSD": ("LTC", "USD"),
    "XXRPZUSD": ("XRP", "USD"),
    "XXLMZUSD": ("XLM", "USD"),
    "XXMRZUSD": ("XMR", "USD"),
    "XZECZUSD": ("ZEC", "USD"),
    "XREPZUSD": ("REP", "USD"),
    "XETCZUSD": ("ETC", "USD"),
}


#: The gateway's exchange name for the club's Kraken Prime account.
EXCHANGE = "kraken_prime"


def _gateway_error_message(e: ProxyError) -> str:
    """A human error string from a gateway failure.

    For a Kraken rejection the gateway relays Kraken's own `error` array
    under `detail["kraken_error"]` (and the whole body under `detail["body"]`).
    """
    detail = e.detail if isinstance(e.detail, dict) else {}
    errors = detail.get("kraken_error") or (detail.get("body") or {}).get("error") or []
    if errors:
        return "; ".join(str(x) for x in errors)
    return e.message or str(e)


class KrakenService(ExchangeService):
    """Kraken service, routed through the CU Quants Proxy to the Prime account.

    The terminal holds no Kraken credentials. Every call is
    `self._proxy.call("kraken_prime", <action>, <payload>)`. The gateway signs
    with the club's vaulted Prime key, adds the Prime `account_id`, enforces
    the allowlist and logs the request. Payloads are Kraken's own field names
    (`pair`, `type`, `ordertype`, `volume`, ...), and responses come back as
    Kraken's own body (`{"error": [], "result": {...}}`), so the parsing below
    is the same as when this service signed its own requests.

    The gateway routes four actions for Prime: `place_order`, `cancel_order`,
    `get_pending_orders` and `get_balance` (Kraken `BalanceEx`). Fills
    (`get_fills`) are not routed yet, so `get_trades` returns an empty list
    until they are.

    There is no live order stream: Kraken's `executions` channel sends no
    updates for Prime orders. The frontend refetches open orders and balances
    after every place and cancel, so the terminal's own actions still show up.
    """

    def __init__(self, proxy: ProxySession):
        super().__init__()
        self._proxy = proxy

    async def _call(self, action: str, payload: Optional[dict] = None, *, mutating: bool = False) -> dict:
        """One gateway call. Mutating calls get a fresh idempotency key."""
        return await self._proxy.call(
            EXCHANGE, action, payload or {},
            idempotency_key=new_idempotency_key() if mutating else "",
        )

    # ------------------------------------------------------------------
    # Pair / asset normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_currency(kraken_asset: str) -> str:
        """XXBT -> BTC, ZUSD -> USD, SOL -> SOL."""
        return _KRAKEN_ASSET_TO_STANDARD.get(kraken_asset, kraken_asset)

    @staticmethod
    def _to_native_pair(pair: str) -> str:
        """BTC/USD -> XBTUSD (for REST request parameters)."""
        base, quote = pair.split("/")
        native_base = _STANDARD_TO_KRAKEN_ASSET.get(base, base)
        # Request-side pairs use the short form (XBTUSD not XXBTZUSD)
        if native_base.startswith("XX"):
            native_base = native_base[1:]
        if native_base.startswith("X") and len(native_base) == 4 and native_base not in ("XETH",):
            pass  # already short
        return f"{native_base}{quote}"

    @staticmethod
    def _from_native_pair(native_pair: str) -> str:
        """XXBTZUSD -> BTC/USD, SOLUSD -> SOL/USD.

        Handles legacy (XXBTZUSD), modern (SOLUSD), and already-normalized
        (BTC/USD) Kraken pair formats.
        """
        if "/" in native_pair:
            return native_pair

        known = _KNOWN_PAIR_PREFIXES.get(native_pair)
        if known:
            return f"{known[0]}/{known[1]}"

        # Modern pairs: strip known quote currency suffixes.
        # Longer suffixes first to avoid partial matches (e.g. USDT before USD).
        for quote in ("USDT", "USDC", "USDD", "USD", "EUR", "GBP", "CAD", "JPY", "AUD"):
            if native_pair.endswith(quote) and len(native_pair) > len(quote):
                base_raw = native_pair[: -len(quote)]
                base = _KRAKEN_ASSET_TO_STANDARD.get(base_raw, base_raw)
                return f"{base}/{quote}"

        # Crypto/crypto: try splitting at 3-4 char boundaries
        for split_pos in (4, 3):
            if len(native_pair) > split_pos:
                base_raw = native_pair[:split_pos]
                quote_raw = native_pair[split_pos:]
                base = _KRAKEN_ASSET_TO_STANDARD.get(base_raw, base_raw)
                quote = _KRAKEN_ASSET_TO_STANDARD.get(quote_raw, quote_raw)
                if base != base_raw or quote != quote_raw:
                    return f"{base}/{quote}"

        logger.warning("Could not parse Kraken pair: %s", native_pair)
        return native_pair

    def _get_quote_ccy(self, pair: str) -> str:
        """BTC/USD -> USD."""
        parts = pair.split("/")
        return parts[1] if len(parts) > 1 else "USD"

    def _get_base_ccy(self, pair: str) -> str:
        """BTC/USD -> BTC."""
        return pair.split("/")[0]

    # ------------------------------------------------------------------
    # REST: orders
    # ------------------------------------------------------------------

    async def place_order(
        self, request: PlaceOrderRequest,
    ) -> Tuple[Optional[OrderResponse], Optional[str]]:
        data = {
            "pair": self._to_native_pair(request.pair),
            "type": request.side,
            "ordertype": request.type,
            "volume": str(request.size),
        }
        if request.type in ("limit", "iceberg") and request.price is not None:
            data["price"] = str(request.price)

        if request.type == "iceberg":
            if request.visible_size is None:
                return (None, "visible_size is required for iceberg orders")
            if request.visible_size > request.size:
                return (None, "visible_size cannot exceed total size")
            if request.visible_size < request.size / 15:
                return (None, "visible_size must be at least 1/15 of total size")
            data["displayvol"] = str(request.visible_size)

        try:
            resp = await self._call("place_order", data, mutating=True)
        except ExchangeError as e:
            if e.outcome_unknown:
                logger.error("Kraken place_order outcome unknown (request %s): %s", e.request_id, e)
                return (None, "Order outcome unknown, check open orders before retrying: "
                              + _gateway_error_message(e))
            return (None, _gateway_error_message(e))
        except ProxyError as e:
            return (None, _gateway_error_message(e))

        result = resp.get("result", {})
        txids = result.get("txid", [])
        order_id = txids[0] if txids else result.get("txid", "")

        order = OrderResponse(
            id=order_id,
            pair=request.pair,
            exchange="kraken",
            side=request.side,
            type=request.type,
            price=request.price,
            visible_size=request.visible_size,
            size=request.size,
            status="live",
        )
        return (order, None)

    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        resp = await self._call("get_pending_orders")
        raw_orders = resp.get("result", {}).get("open", {})

        orders: List[OrderResponse] = []
        for txid, item in raw_orders.items():
            descr = item.get("descr", {})
            item_pair = self._from_native_pair(descr.get("pair", ""))

            if pair and item_pair != pair:
                continue

            raw_ordertype = descr.get("ordertype", "")
            if raw_ordertype == "iceberg":
                order_type = "iceberg"
            elif raw_ordertype in ("market", "stop-loss", "take-profit", "trailing-stop"):
                order_type = "market"
            else:
                order_type = "limit"

            display_vol_str = item.get("display_volume")
            visible_size = float(display_vol_str) if display_vol_str else None

            orders.append(OrderResponse(
                id=txid,
                pair=item_pair,
                exchange="kraken",
                side=descr.get("type", ""),
                type=order_type,
                price=float(descr["price"]) if descr.get("price") and descr["price"] != "0" else None,
                visible_size=visible_size,
                size=float(item.get("vol", 0)),
                status=item.get("status", "open"),
                created_at=str(item.get("opentm", "")),
            ))

        return orders

    async def get_trades(
        self, pair: Optional[str] = None, limit: int = 100,
    ) -> List[TradeResponse]:
        extra: dict = {}
        if pair:
            extra["pair"] = self._to_native_pair(pair)

        try:
            resp = await self._call("get_fills", extra)
        except ActionNotPermittedError:
            # Not routed for Prime yet. Starts working once the gateway routes it.
            logger.info("Kraken fills are not routed through the gateway yet; returning none")
            return []
        raw_trades = resp.get("result", {}).get("trades", {})

        trades: List[TradeResponse] = []
        for trade_id, item in raw_trades.items():
            if len(trades) >= limit:
                break
            native_pair = item.get("pair", "")
            fee_str = item.get("fee", "0")
            trades.append(TradeResponse(
                id=trade_id,
                order_id=item.get("ordertxid", ""),
                pair=self._from_native_pair(native_pair),
                exchange="kraken",
                side=item.get("type", ""),
                price=float(item.get("price", 0)),
                size=float(item.get("vol", 0)),
                fee=abs(float(fee_str)),
                fee_currency=self._get_quote_ccy(self._from_native_pair(native_pair)),
                role="maker" if item.get("misc") == "maker" else "taker",
                timestamp=str(item.get("time", "")),
            ))
        return trades

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        try:
            resp = await self._call("cancel_order", {"txid": order_id}, mutating=True)
        except ProxyError as e:
            logger.warning("Kraken cancel_order %s failed: %s", order_id, _gateway_error_message(e))
            return False
        return (resp.get("result") or {}).get("count", 0) >= 1

    # ------------------------------------------------------------------
    # REST: account balance
    # ------------------------------------------------------------------

    async def _fetch_all_balances(self) -> Dict[str, Tuple[float, float]]:
        """Standard currency -> (total, frozen), from Kraken `BalanceEx`.

        `BalanceEx` rows are `{"balance": "...", "hold_trade": "..."}`: the
        total and the part held by open orders. Asset codes are normalized
        here (XXBT -> BTC, ZUSD -> USD) so every lookup below is by the
        standard name, and two codes for the same currency are added together.
        """
        resp = await self._call("get_balance")
        out: Dict[str, Tuple[float, float]] = {}
        for raw_ccy, row in (resp.get("result") or {}).items():
            if isinstance(row, dict):
                total = float(row.get("balance") or 0)
                frozen = float(row.get("hold_trade") or 0)
            else:  # plain `Balance` shape: {"ZUSD": "1000.0"}
                total, frozen = float(row or 0), 0.0
            ccy = self._normalize_currency(raw_ccy)
            prev_total, prev_frozen = out.get(ccy, (0.0, 0.0))
            out[ccy] = (prev_total + total, prev_frozen + frozen)
        return out

    @staticmethod
    def _split(total: float, frozen: float) -> Tuple[float, float, float]:
        """(available, frozen, total)."""
        return max(total - frozen, 0.0), frozen, total

    async def get_available_cash(self, pair: str) -> AvailableCashResponse:
        balances = await self._fetch_all_balances()
        ccy = self._get_quote_ccy(pair)
        available, frozen, total = self._split(*balances.get(ccy, (0.0, 0.0)))
        return AvailableCashResponse(
            exchange="kraken",
            currency=ccy,
            available=available,
            frozen=frozen,
            total=total,
        )

    async def get_available_positions(self, pair: str) -> AvailablePositionResponse:
        balances = await self._fetch_all_balances()
        ccy = self._get_base_ccy(pair)
        available, frozen, total = self._split(*balances.get(ccy, (0.0, 0.0)))
        return AvailablePositionResponse(
            exchange="kraken",
            pair=pair,
            base_currency=ccy,
            available=available,
            frozen=frozen,
            total=total,
        )

    _CASH_CCYS = frozenset({"USD", "EUR", "GBP", "CAD", "JPY", "AUD", "USDT", "USDC", "DAI"})

    async def get_all_balances(self) -> AllBalancesResponse:
        balances = await self._fetch_all_balances()
        currencies: List[BalanceEntry] = []
        for ccy, (total, frozen) in balances.items():
            available, frozen, total = self._split(total, frozen)
            currencies.append(BalanceEntry(
                currency=ccy,
                available=available,
                frozen=frozen,
                total=total,
            ))
        return AllBalancesResponse(exchange="kraken", currencies=currencies)

    async def get_all_positions(self) -> AllPositionsResponse:
        balances = await self._fetch_all_balances()
        positions: List[PositionEntry] = []
        for ccy, (total, frozen) in balances.items():
            if ccy in self._CASH_CCYS or total <= 0:
                continue
            available, frozen, total = self._split(total, frozen)
            positions.append(PositionEntry(
                currency=ccy,
                available=available,
                frozen=frozen,
                total=total,
            ))
        return AllPositionsResponse(exchange="kraken", positions=positions)

    # ------------------------------------------------------------------
    # Order event stream: none for Prime
    # ------------------------------------------------------------------

    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        """No-op. Kraken's `executions` channel sends no updates for Prime
        orders, and the gateway offers no WebSocket for `kraken_prime`."""
        return None

    async def stop_order_stream(self) -> None:
        return None
