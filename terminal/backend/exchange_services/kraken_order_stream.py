import asyncio
import hashlib
import hmac
import base64
import json
import logging
import time
import urllib.parse
from typing import Optional

import httpx
import websockets

from exchange_services.order_event_stream_base import BaseOrderEventStream

logger = logging.getLogger(__name__)

KRAKEN_STATUS_MAP = {
    "new": "live",
    "partially_filled": "partially_filled",
    "filled": "filled",
    "canceled": "canceled",
    "expired": "canceled",
}

# exec_type values that represent meaningful order lifecycle transitions
_RELEVANT_EXEC_TYPES = frozenset({
    "new", "trade", "filled", "canceled", "expired",
    "amended", "iceberg_refill", "restated",
})

# Events that signal the order is fully done and can be evicted from the cache
_TERMINAL_STATUSES = frozenset({"filled", "canceled", "expired"})


class KrakenOrderStream(BaseOrderEventStream):
    """Authenticated WebSocket (v2) connection to Kraken for streaming
    real-time order execution events.

    Obtains a session token via the REST API, then subscribes to the
    ``executions`` channel on ``wss://ws-auth.kraken.com/v2``.

    Lifecycle: start() opens the connection and pushes normalized events
    into the provided asyncio.Queue.  stop() tears it down.  Reconnects
    automatically with exponential backoff on transient failures (handled
    by BaseOrderEventStream).
    """

    WS_URL = "wss://ws-auth.kraken.com/v2"
    PING_INTERVAL_S = 30

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.kraken.com",
    ):
        super().__init__(exchange_name="kraken")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url
        self._token: Optional[str] = None
        self._order_symbols: dict[str, str] = {}

    # ------------------------------------------------------------------
    # REST: obtain WS session token
    # ------------------------------------------------------------------

    def _sign(self, urlpath: str, data: dict) -> str:
        post_data = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + post_data).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self._api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    async def _fetch_ws_token(self) -> str:
        """POST /0/private/GetWebSocketsToken to obtain a short-lived session token."""
        urlpath = "/0/private/GetWebSocketsToken"
        data = {"nonce": str(int(time.time() * 1000))}
        body = urllib.parse.urlencode(data)
        headers = {
            "API-Key": self._api_key,
            "API-Sign": self._sign(urlpath, data),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self._base_url}{urlpath}", content=body, headers=headers)
            resp.raise_for_status()
            payload = resp.json()

        errors = payload.get("error", [])
        if errors:
            raise ConnectionError(f"Kraken GetWebSocketsToken failed: {errors}")

        token = payload.get("result", {}).get("token")
        if not token:
            raise ConnectionError("Kraken GetWebSocketsToken returned no token")
        return token

    # ------------------------------------------------------------------
    # WS: connection, subscription, streaming
    # ------------------------------------------------------------------

    async def _connect_and_stream(self, event_queue: asyncio.Queue) -> None:
        self._token = await self._fetch_ws_token()
        self._order_symbols.clear()

        async with websockets.connect(self.WS_URL) as ws:
            self._ws = ws

            await self._subscribe_executions(ws)
            await self._emit_status_async(event_queue, "connected")

            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    channel = msg.get("channel")
                    if channel != "executions":
                        continue

                    msg_type = msg.get("type")
                    if msg_type not in ("snapshot", "update"):
                        continue

                    for item in msg.get("data", []):
                        self._track_order_symbol(item)
                        event = self._normalize_order_event(item)
                        if event:
                            await event_queue.put(event)
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

    async def _subscribe_executions(self, ws) -> None:
        subscribe_msg = json.dumps({
            "method": "subscribe",
            "params": {
                "channel": "executions",
                "token": self._token,
                "snap_orders": True,
                "snap_trades": False,
            },
        })
        await ws.send(subscribe_msg)

        # Kraken sends system status messages before the subscribe ack.
        # Keep reading until we get the actual subscribe response.
        deadline = asyncio.get_event_loop().time() + 10
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise ConnectionError("Kraken WS subscribe timed out")
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            resp = json.loads(raw)
            if resp.get("method") == "subscribe":
                if not resp.get("success", False):
                    raise ConnectionError(f"Kraken WS subscribe failed: {resp}")
                return

    async def _ping_loop(self, ws) -> None:
        try:
            while True:
                await asyncio.sleep(self.PING_INTERVAL_S)
                await ws.send(json.dumps({"method": "ping"}))
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    # ------------------------------------------------------------------
    # Order symbol cache
    # ------------------------------------------------------------------

    def _track_order_symbol(self, item: dict) -> None:
        """Populate / evict the order_id -> symbol cache."""
        order_id = item.get("order_id", "")
        if not order_id:
            return

        symbol = item.get("symbol")
        if symbol:
            self._order_symbols[order_id] = symbol

        if item.get("exec_type") in _TERMINAL_STATUSES:
            self._order_symbols.pop(order_id, None)

    def update_symbol_cache(self, order_symbols: dict[str, str]) -> None:
        """Bulk-update the order_id -> symbol cache from an external source (REST)."""
        self._order_symbols.update(order_symbols)

    def _resolve_symbol(self, item: dict) -> str:
        """Return the symbol from the event, falling back to the cache."""
        symbol = item.get("symbol")
        if symbol:
            return symbol
        return self._order_symbols.get(item.get("order_id", ""), "")

    # ------------------------------------------------------------------
    # Event normalization
    # ------------------------------------------------------------------

    def _normalize_order_event(self, item: dict) -> Optional[dict]:
        exec_type = item.get("exec_type", "")
        if exec_type not in _RELEVANT_EXEC_TYPES:
            return None

        order_status = item.get("order_status", "")
        status = KRAKEN_STATUS_MAP.get(order_status)
        if not status:
            return None

        symbol = self._resolve_symbol(item)
        if not symbol:
            logger.warning(
                "Kraken order event missing symbol (order_id=%s, exec_type=%s)",
                item.get("order_id"), exec_type,
            )
            return None

        price = item.get("limit_price") or item.get("avg_price") or item.get("last_price") or 0
        size = item.get("order_qty") or item.get("cum_qty") or 0

        return {
            "type": "order_event",
            "exchange": "kraken",
            "pair": symbol,
            "orderId": item.get("order_id", ""),
            "status": status,
            "side": item.get("side", ""),
            "price": float(price),
            "size": float(size),
            "timestamp": item.get("timestamp", ""),
        }
