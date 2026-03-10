import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import urlencode
from typing import Callable

import httpx
import websockets

logger = logging.getLogger(__name__)

KRAKEN_STATE_MAP = {
    "pending_new": "live",
    "new": "live",
    "partially_filled": "partially_filled",
    "filled": "filled",
    "canceled": "canceled",
    "expired": "canceled", # Mapping expired to canceled, we'll probably want to change this
    "rejected": "rejected",
}


class KrakenOrderEventStream:
    """Authenticated WebSocket v2 stream for Kraken order lifecycle events."""

    WS_URL = "wss://ws-auth.kraken.com/v2"
    REST_URL = "https://api.kraken.com"
    TOKEN_PATH = "/0/private/GetWebSocketsToken"
    MAX_RETRIES = 3
    BACKOFF_DELAYS_S = [1, 2, 4]

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        pair_normalizer: Callable[[str], str] = lambda x: x,
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._normalize_pair = pair_normalizer
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._order_cache: dict[str, dict] = {}

    async def start(self, event_queue: asyncio.Queue) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(event_queue))

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._order_cache.clear()

    def _rest_sign(self, nonce: str, post_data: str, path: str) -> str:
        """Generate Kraken API-Sign for private REST requests."""
        sha256 = hashlib.sha256((nonce + post_data).encode()).digest()
        message = path.encode() + sha256
        secret = base64.b64decode(self._api_secret)
        mac = hmac.new(secret, message, hashlib.sha512).digest()
        return base64.b64encode(mac).decode()

    async def _fetch_ws_token(self) -> str:
        nonce = str(int(time.time() * 1000))
        post_data = urlencode({"nonce": nonce})
        sign = self._rest_sign(nonce, post_data, self.TOKEN_PATH)
        headers = {
            "API-Key": self._api_key,
            "API-Sign": sign,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with httpx.AsyncClient(base_url=self.REST_URL, timeout=10) as client:
            resp = await client.post(
                self.TOKEN_PATH, content=post_data, headers=headers
            )
            resp.raise_for_status()
            payload = resp.json()

        if payload.get("error"):
            raise ConnectionError(
                f"Kraken WS token fetch failed: {payload.get('error')}"
            )

        token = (payload.get("result") or {}).get("token")
        if not token:
            raise ConnectionError(f"Kraken WS token missing in response: {payload}")
        return token

    @staticmethod
    def _build_subscribe_msg(token: str) -> str:
        return json.dumps(
            {
                "method": "subscribe",
                "params": {
                    "channel": "executions",
                    "token": token,
                    "snap_orders": True,
                    "snap_trades": False,
                    "order_status": True,
                },
            }
        )

    async def _run_loop(self, event_queue: asyncio.Queue) -> None:
        retries = 0

        while self._running:
            try:
                await self._connect_and_stream(event_queue)
                if not self._running:
                    break
                retries = 0
            except (
                websockets.ConnectionClosed,
                OSError,
                asyncio.TimeoutError,
                httpx.HTTPError,
            ) as exc:
                if not self._running:
                    break
                retries += 1
                logger.warning(
                    "Kraken private WS lost (attempt %d/%d): %s",
                    retries,
                    self.MAX_RETRIES,
                    exc,
                )
                if retries >= self.MAX_RETRIES:
                    await event_queue.put(
                        {
                            "type": "status",
                            "exchange": "kraken",
                            "connectionStatus": "disconnected",
                        }
                    )
                    break
                await event_queue.put(
                    {
                        "type": "status",
                        "exchange": "kraken",
                        "connectionStatus": "reconnecting",
                    }
                )
                delay = self.BACKOFF_DELAYS_S[
                    min(retries - 1, len(self.BACKOFF_DELAYS_S) - 1)
                ]
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "Kraken private WS unexpected error: %s", exc, exc_info=True
                )
                await event_queue.put(
                    {
                        "type": "status",
                        "exchange": "kraken",
                        "connectionStatus": "disconnected",
                    }
                )
                break

    async def _connect_and_stream(self, event_queue: asyncio.Queue) -> None:
        self._order_cache.clear()
        token = await self._fetch_ws_token()

        async with websockets.connect(
            self.WS_URL, ping_interval=20, ping_timeout=10
        ) as ws:
            self._ws = ws
            await self._subscribe_executions(ws, token)

            await event_queue.put(
                {
                    "type": "status",
                    "exchange": "kraken",
                    "connectionStatus": "connected",
                }
            )

            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if data.get("channel") != "executions":
                    continue

                for item in data.get("data", []):
                    event = self._normalize_order_event(item)
                    if event:
                        await event_queue.put(event)

    async def _subscribe_executions(self, ws, token: str) -> None:
        await ws.send(self._build_subscribe_msg(token))

        while True:
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))

            if resp.get("method") == "subscribe" and resp.get("success") is False:
                raise ConnectionError(f"Kraken WS subscribe failed: {resp}")

            if (
                resp.get("method") == "subscribe"
                and resp.get("success") is True
                and resp.get("result", {}).get("channel") == "executions"
            ):
                return

    def _normalize_order_event(self, item: dict) -> dict | None:
        order_id = item.get("order_id")
        if not order_id:
            return None

        raw_status = item.get("order_status")
        status = KRAKEN_STATE_MAP.get(raw_status)
        if not status:
            return None

        cache = self._order_cache.setdefault(order_id, {})
        if item.get("symbol"):
            cache["symbol"] = item["symbol"]
        if item.get("side"):
            cache["side"] = item["side"]
        if item.get("order_qty") is not None:
            cache["order_qty"] = item["order_qty"]
        if item.get("limit_price") is not None:
            cache["limit_price"] = item["limit_price"]

        symbol = item.get("symbol") or cache.get("symbol") or ""
        side = item.get("side") or cache.get("side") or ""
        qty = item.get("order_qty", cache.get("order_qty", 0))
        price = item.get("limit_price", cache.get("limit_price", 0))
        timestamp = item.get("timestamp") or item.get("last_update_time") or ""
        event = {
            "type": "order_event",
            "exchange": "kraken",
            "pair": self._normalize_pair(symbol),
            "orderId": order_id,
            "status": status,
            "side": side,
            "price": float(price or 0),
            "size": float(qty or 0),
            "timestamp": timestamp,
        }
        if status in {"filled", "canceled", "rejected"}:
            self._order_cache.pop(order_id, None)
        return event
