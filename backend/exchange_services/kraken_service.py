import asyncio
import hashlib
import hmac
import base64
import logging
import os
import threading
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

from exchange_services.exchange import ExchangeService
from exchange_services.kraken_order_stream import KrakenOrderStream
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


class KrakenService(ExchangeService):
    """Kraken spot exchange service.

    Handles REST authentication (HMAC-SHA512 + nonce), pair normalization
    between standard (BTC/USD) and Kraken-native formats, and order/balance
    operations.  Wires up a KrakenOrderStream for live order events.
    """

    def __init__(self, base_url: str = "https://api.kraken.com", simulated: bool = False):
        super().__init__(base_url)
        self.api_key = os.getenv("KRAKEN_API_KEY", "")
        self.api_secret = os.getenv("KRAKEN_API_SECRET", "")
        self.simulated = simulated
        self._order_stream: KrakenOrderStream | None = None

    def _feed_order_symbols(self, mappings: dict[str, str]) -> None:
        """Push order_id -> symbol mappings into the WS stream's cache."""
        if self._order_stream:
            self._order_stream.update_symbol_cache(mappings)

    # ------------------------------------------------------------------
    # Auth / signing (REST)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_nonce() -> str:
        return str(int(time.time() * 1000))

    def _sign(self, urlpath: str, data: dict) -> str:
        """HMAC-SHA512 signature per Kraken docs:
        sign = HMAC-SHA512(urlpath + SHA256(nonce + POST_data), base64decode(secret))
        """
        post_data = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + post_data).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    async def _private_request(self, path: str, extra_data: Optional[dict] = None) -> dict:
        """Authenticated POST to a Kraken private endpoint.

        Adds nonce, signs, and sends form-encoded body through the inherited
        ``_request`` helper.
        """
        data: dict = {"nonce": self._get_nonce()}
        if extra_data:
            data.update(extra_data)

        urlpath = f"/0{path}"
        body = urllib.parse.urlencode(data)
        headers = {
            "API-Key": self.api_key,
            "API-Sign": self._sign(urlpath, data),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = await self._request("POST", urlpath, body=body, headers=headers)
        errors = resp.get("error", [])
        if errors:
            raise Exception("; ".join(errors))
        return resp

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

    def _find_balance_for(self, balances: Dict[str, str], standard_ccy: str) -> float:
        """Look up a balance by standard currency name, checking all Kraken aliases."""
        # Direct match (e.g. SOL, DOT)
        if standard_ccy in balances:
            return float(balances[standard_ccy])
        # Reverse-lookup the Kraken key
        kraken_key = _STANDARD_TO_KRAKEN_ASSET.get(standard_ccy)
        if kraken_key and kraken_key in balances:
            return float(balances[kraken_key])
        return 0.0

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
            resp = await self._private_request("/private/AddOrder", data)
        except Exception as e:
            return (None, str(e))

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
        self._feed_order_symbols({order_id: request.pair})
        return (order, None)

    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        resp = await self._private_request("/private/OpenOrders")
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

        self._feed_order_symbols({o.id: o.pair for o in orders})
        return orders

    async def get_trades(
        self, pair: Optional[str] = None, limit: int = 100,
    ) -> List[TradeResponse]:
        extra: dict = {}
        if pair:
            extra["pair"] = self._to_native_pair(pair)

        resp = await self._private_request("/private/TradesHistory", extra)
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
            await self._private_request("/private/CancelOrder", {"txid": order_id})
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # REST: account balance
    # ------------------------------------------------------------------

    async def _fetch_all_balances(self) -> Dict[str, str]:
        resp = await self._private_request("/private/Balance")
        return resp.get("result", {})

    async def get_available_cash(self, pair: str) -> AvailableCashResponse:
        balances = await self._fetch_all_balances()
        ccy = self._get_quote_ccy(pair)
        total = self._find_balance_for(balances, ccy)
        return AvailableCashResponse(
            exchange="kraken",
            currency=ccy,
            available=total,
            frozen=0.0,
            total=total,
        )

    async def get_available_positions(self, pair: str) -> AvailablePositionResponse:
        balances = await self._fetch_all_balances()
        ccy = self._get_base_ccy(pair)
        total = self._find_balance_for(balances, ccy)
        return AvailablePositionResponse(
            exchange="kraken",
            pair=pair,
            base_currency=ccy,
            available=total,
            frozen=0.0,
            total=total,
        )

    _CASH_CCYS = frozenset({"USD", "EUR", "GBP", "CAD", "JPY", "AUD", "USDT", "USDC", "DAI"})

    async def get_all_balances(self) -> AllBalancesResponse:
        balances = await self._fetch_all_balances()
        currencies: List[BalanceEntry] = []
        for raw_ccy, raw_val in balances.items():
            ccy = self._normalize_currency(raw_ccy)
            total = float(raw_val)
            currencies.append(BalanceEntry(
                currency=ccy,
                available=total,
                frozen=0.0,
                total=total,
            ))
        return AllBalancesResponse(exchange="kraken", currencies=currencies)

    async def get_all_positions(self) -> AllPositionsResponse:
        balances = await self._fetch_all_balances()
        positions: List[PositionEntry] = []
        for raw_ccy, raw_val in balances.items():
            ccy = self._normalize_currency(raw_ccy)
            if ccy in self._CASH_CCYS:
                continue
            total = float(raw_val)
            if total <= 0:
                continue
            positions.append(PositionEntry(
                currency=ccy,
                available=total,
                frozen=0.0,
                total=total,
            ))
        return AllPositionsResponse(exchange="kraken", positions=positions)

    # ------------------------------------------------------------------
    # WS: order event stream
    # ------------------------------------------------------------------

    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        if self._order_stream is not None:
            return
        self._order_stream = KrakenOrderStream(
            api_key=self.api_key,
            api_secret=self.api_secret,
            base_url=self.base_url,
        )
        await self._order_stream.start(event_queue)

    async def stop_order_stream(self) -> None:
        if self._order_stream:
            await self._order_stream.stop()
            self._order_stream = None
