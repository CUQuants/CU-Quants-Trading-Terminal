import asyncio
import hashlib
import hmac
import base64
import json
import os
import time
import logging
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from typing import Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
load_dotenv()

from exchange_services.exchange import ExchangeService
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


class GeminiService(ExchangeService):
    """Gemini exchange service. Inherits from ExchangeService."""

    _CASH_CCYS = frozenset({"USD", "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD", "GUSD"})

    def __init__(self, base_url: str = "https://api.gemini.com", simulated: bool = False):
        if simulated:
            base_url = "https://api.sandbox.gemini.com"
        super().__init__(base_url)
        self.simulated = simulated
        if simulated:
            self.api_key = os.getenv("GEMINI_API_KEY_SIMULATED", "")
            self.api_secret = os.getenv("GEMINI_API_SECRET_SIMULATED", "")
            self.account = os.getenv("GEMINI_ACCOUNT_SIMULATED", "")
        else:
            self.api_key = os.getenv("GEMINI_API_KEY", "")
            self.api_secret = os.getenv("GEMINI_API_SECRET", "")
            self.account = os.getenv("GEMINI_ACCOUNT", "")

        self.account = self.account.strip()
        self.is_master_api_key = self.api_key.startswith("master-")
        if self.is_master_api_key and not self.account:
            self.account = "primary"

        slippage_bps_raw = os.getenv("GEMINI_MARKET_SLIPPAGE_BPS", "50").strip()
        try:
            slippage_bps = float(slippage_bps_raw)
        except ValueError:
            slippage_bps = 50.0
        # Clamp to a sane range (0.01% .. 5.00%).
        self.market_slippage_bps = min(max(slippage_bps, 1.0), 500.0)
        self._quote_increment_cache: Dict[str, Decimal] = {}
    # ------------------------------------------------------------------
    # Auth / signing
    # ------------------------------------------------------------------

    def _get_nonce(self) -> int:
        return int(time.time() * 1000)

    def _get_headers(self, payload: dict) -> dict:
        payload_json = json.dumps(payload)
        payload_b64 = base64.b64encode(payload_json.encode()).decode()
        signature = hmac.new(
            self.api_secret.encode(),
            payload_b64.encode(),
            hashlib.sha384,
        ).hexdigest()
        return {
            "Content-Type": "text/plain",
            "Content-Length": "0",
            "Accept": "application/json",
            "X-GEMINI-APIKEY": self.api_key,
            "X-GEMINI-PAYLOAD": payload_b64,
            "X-GEMINI-SIGNATURE": signature,
            "Cache-Control": "no-cache",
        }

    # ------------------------------------------------------------------
    # HTTP helper – override base to send empty body (Gemini puts data in headers)
    # ------------------------------------------------------------------

    async def _gemini_request(self, method: str, path: str, payload: dict) -> dict:
        """Build auth headers from *payload*, send with empty body, return JSON."""
        if self.account:
            payload.setdefault("account", self.account)
        headers = self._get_headers(payload)
        return await self._request(method, path, body="", headers=headers)

    async def _resolve_market_ioc_price(self, symbol: str, side: str, explicit_price: Optional[float]) -> str:
        """Use a near-touch IOC price to emulate market orders on Gemini."""
        if explicit_price is not None:
            return await self._normalize_price(symbol, side, explicit_price)

        try:
            ticker = await self._request("GET", f"/v2/ticker/{symbol}")
            if side == "buy":
                ref = float(ticker.get("ask") or ticker.get("last") or ticker.get("bid") or 0)
            else:
                ref = float(ticker.get("bid") or ticker.get("last") or ticker.get("ask") or 0)
        except Exception:
            ref = 0.0

        if ref > 0:
            slip = self.market_slippage_bps / 10_000
            buffered = ref * (1 + slip if side == "buy" else 1 - slip)
            return await self._normalize_price(symbol, side, buffered)

        # Fallback to permissive limits if ticker lookup fails.
        return "999999" if side == "buy" else "0.01"

    async def _get_quote_increment(self, symbol: str) -> Decimal:
        cached = self._quote_increment_cache.get(symbol)
        if cached is not None:
            return cached

        increment = Decimal("0.01")
        try:
            details = await self._request("GET", f"/v1/symbols/details/{symbol}")
            raw_increment = details.get("quote_increment") or details.get("tick_size")
            if raw_increment:
                increment = Decimal(str(raw_increment))
        except Exception:
            pass

        if increment <= 0:
            increment = Decimal("0.01")
        self._quote_increment_cache[symbol] = increment
        return increment

    async def _normalize_price(self, symbol: str, side: str, raw_price: float) -> str:
        increment = await self._get_quote_increment(symbol)
        price = Decimal(str(raw_price))
        if price <= 0:
            price = increment

        # Keep IOC emulation aggressive while staying on a valid tick.
        rounding = ROUND_CEILING if side == "buy" else ROUND_FLOOR
        normalized = (price / increment).to_integral_value(rounding=rounding) * increment
        if normalized <= 0:
            normalized = increment
        return format(normalized.normalize(), "f")

    @staticmethod
    def _extract_error_message(exc: Exception) -> str:
        """Extract useful error details from Gemini HTTP responses."""
        if not isinstance(exc, httpx.HTTPStatusError):
            return str(exc)

        response = exc.response
        try:
            payload = response.json()
            if isinstance(payload, dict):
                reason = payload.get("reason")
                message = payload.get("message")
                if reason and message:
                    return f"{reason}: {message}"
                if message:
                    return str(message)
                if reason:
                    return str(reason)
        except Exception:
            pass

        text = (response.text or "").strip()
        if text:
            return f"HTTP {response.status_code}: {text}"
        return str(exc)

    # ------------------------------------------------------------------
    # Pair normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _to_native_pair(pair: str) -> str:
        """BTC/USD -> btcusd"""
        base, quote = pair.split("/")
        return f"{base}{quote}".lower()

    @staticmethod
    def _from_native_pair(native: str) -> str:
        """btcusd -> BTC/USD
        Gemini symbols are lowercase concatenated pairs. The quote is always
        the last 3 characters (USD, BTC, ETH, etc.) for standard pairs.
        """
        native = native.upper()
        if native.endswith("USD"):
            return f"{native[:-3]}/USD"
        if native.endswith("BTC"):
            return f"{native[:-3]}/BTC"
        if native.endswith("ETH"):
            return f"{native[:-3]}/ETH"
        return native

    # ------------------------------------------------------------------
    # REST: orders
    # ------------------------------------------------------------------

    async def place_order(
        self, request: PlaceOrderRequest
    ) -> Tuple[Optional[OrderResponse], Optional[str]]:
        request_path = "/v1/order/new"
        symbol = self._to_native_pair(request.pair)
        payload = {
            "request": request_path,
            "nonce": self._get_nonce(),
            "symbol": symbol,
            "amount": str(request.size),
            "side": request.side,
            "type": "exchange limit",
        }

        if request.type == "market":
            payload["price"] = await self._resolve_market_ioc_price(symbol, request.side, request.price)
            payload["options"] = ["immediate-or-cancel"]
        else:
            if request.price is None:
                return (None, "Limit orders require price")
            payload["price"] = await self._normalize_price(symbol, request.side, request.price)

        try:
            data = await self._gemini_request("POST", request_path, payload)
        except Exception as e:
            return (None, self._extract_error_message(e))

        if isinstance(data, dict) and data.get("result") == "error":
            msg = data.get("message") or data.get("reason") or "Order failed"
            return (None, msg)

        order = OrderResponse(
            id=str(data["order_id"]),
            pair=request.pair,
            exchange="gemini",
            side=request.side,
            type=request.type,
            price=request.price,
            size=request.size,
            status="live" if data.get("is_live") else "closed",
            created_at=data.get("timestamp"),
        )
        return (order, None)

    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        request_path = "/v1/orders"
        payload = {
            "request": request_path,
            "nonce": self._get_nonce(),
        }
        data = await self._gemini_request("POST", request_path, payload)

        orders: List[OrderResponse] = []
        for item in data:
            item_pair = self._from_native_pair(item["symbol"])
            if pair and item_pair != pair:
                continue
            ord_type = "market" if "immediate-or-cancel" in item.get("options", []) else "limit"
            status = "live" if item.get("is_live") else "cancelled" if item.get("is_cancelled") else "closed"
            orders.append(OrderResponse(
                id=str(item["order_id"]),
                pair=item_pair,
                exchange="gemini",
                side=item["side"],
                type=ord_type,
                price=float(item["price"]) if item.get("price") else None,
                size=float(item["original_amount"]),
                status=status,
                created_at=item.get("timestamp"),
            ))
        return orders

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        request_path = "/v1/order/cancel"
        payload = {
            "request": request_path,
            "nonce": self._get_nonce(),
            "order_id": order_id,
        }

        try:
            data = await self._gemini_request("POST", request_path, payload)
        except Exception:
            return False

        if isinstance(data, dict) and data.get("result") == "error":
            return False
        return data.get("is_cancelled", False)

    async def get_trades(self, pair: Optional[str] = None, limit: int = 100) -> List[TradeResponse]:
        request_path = "/v1/mytrades"
        payload: dict = {
            "request": request_path,
            "nonce": self._get_nonce(),
            "limit_trades": limit,
        }
        if pair:
            payload["symbol"] = self._to_native_pair(pair)

        data = await self._gemini_request("POST", request_path, payload)

        trades: List[TradeResponse] = []
        for item in data:
            side_raw = item.get("side", item.get("type", "")).lower()
            side = "buy" if side_raw == "buy" else "sell"
            is_maker = item.get("is_maker", not item.get("aggressor", True))
            trades.append(TradeResponse(
                id=str(item["tid"]),
                order_id=str(item["order_id"]),
                pair=self._from_native_pair(item["symbol"]),
                exchange="gemini",
                side=side,
                price=float(item["price"]),
                size=float(item["amount"]),
                fee=abs(float(item.get("fee_amount", 0))),
                fee_currency=item.get("fee_currency", ""),
                role="maker" if is_maker else "taker",
                timestamp=str(item.get("timestampms", item.get("timestamp", ""))),
            ))
        return trades

    # ------------------------------------------------------------------
    # REST: account balance
    # ------------------------------------------------------------------

    async def _fetch_all_balances(self) -> List[dict]:
        request_path = "/v1/balances"
        payload = {
            "request": request_path,
            "nonce": self._get_nonce(),
        }
        return await self._gemini_request("POST", request_path, payload)

    async def get_available_cash(self, pair: str) -> AvailableCashResponse:
        balances = await self._fetch_all_balances()
        _, quote = pair.split("/")
        ccy = quote

        entry = next((b for b in balances if b["currency"] == ccy), None)
        if entry:
            available = float(entry.get("available", 0))
            total = float(entry.get("amount", 0))
        else:
            available = 0.0
            total = 0.0
        frozen = total - available

        return AvailableCashResponse(
            exchange="gemini",
            currency=ccy,
            available=available,
            frozen=frozen,
            total=total,
        )

    async def get_available_positions(self, pair: str) -> AvailablePositionResponse:
        balances = await self._fetch_all_balances()
        base, _ = pair.split("/")

        entry = next((b for b in balances if b["currency"] == base), None)
        if entry:
            available = float(entry.get("available", 0))
            total = float(entry.get("amount", 0))
        else:
            available = 0.0
            total = 0.0
        frozen = total - available

        return AvailablePositionResponse(
            exchange="gemini",
            pair=pair,
            base_currency=base,
            available=available,
            frozen=frozen,
            total=total,
        )

    async def get_all_balances(self) -> AllBalancesResponse:
        balances = await self._fetch_all_balances()
        currencies = []
        for b in balances:
            available = float(b.get("available", 0))
            total = float(b.get("amount", 0))
            frozen = total - available
            currencies.append(BalanceEntry(
                currency=b["currency"],
                available=available,
                frozen=frozen,
                total=total,
            ))
        return AllBalancesResponse(exchange="gemini", currencies=currencies)

    async def get_all_positions(self) -> AllPositionsResponse:
        balances = await self._fetch_all_balances()
        positions = []
        for b in balances:
            ccy = b["currency"]
            if ccy in self._CASH_CCYS:
                continue
            available = float(b.get("available", 0))
            total = float(b.get("amount", 0))
            if total <= 0:
                continue
            frozen = total - available
            positions.append(PositionEntry(
                currency=ccy,
                available=available,
                frozen=frozen,
                total=total,
            ))
        return AllPositionsResponse(exchange="gemini", positions=positions)

    # ------------------------------------------------------------------
    # WS: order event stream (not implemented yet)
    # ------------------------------------------------------------------

    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        pass

    async def stop_order_stream(self) -> None:
        pass
