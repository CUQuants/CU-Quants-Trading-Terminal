import asyncio
import hmac
import hashlib
import base64
import json
import time
import logging
from typing import Callable

import websockets

logger = logging.getLogger(__name__)

OKX_STATE_MAP = {
    "live": "live",
    "partially_filled": "partially_filled",
    "filled": "filled",
    "canceled": "canceled",
    "mmp_canceled": "canceled",
}


class OkxOrderEventStream:
    """Authenticated WebSocket connection to OKX's private API
    for streaming real-time order events.

    Lifecycle: start() opens the connection and begins pushing normalized
    events into the provided asyncio.Queue. stop() tears it down.
    Reconnects automatically with exponential backoff on transient failures.
    """

    WS_URL_US = "wss://wsus.okx.com:8443/ws/v5/private"
    WS_URL_GLOBAL = "wss://ws.okx.com:8443/ws/v5/private"
    WS_URL_DEMO = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
    PING_INTERVAL_S = 25
    MAX_RETRIES = 3
    BACKOFF_DELAYS_S = [1, 2, 4]

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        simulated: bool = False,
        us: bool = True,
        pair_normalizer: Callable[[str], str] = lambda x: x,
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        self._simulated = simulated
        self._us = us
        if us:
            self._ws_url = self.WS_URL_US
        else:
            self._ws_url = self.WS_URL_DEMO if simulated else self.WS_URL_GLOBAL
        self._normalize_pair = pair_normalizer
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def _ws_sign(self, timestamp: str) -> str:
        """HMAC-SHA256 signature for OKX private WS login.
        Prehash: <unix_ts_seconds>GET/users/self/verify
        """
        prehash = timestamp + "GET" + "/users/self/verify"
        mac = hmac.new(
            self._api_secret.encode(),
            prehash.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(mac).decode()

    def _build_login_msg(self) -> str:
        ts = str(int(time.time()))
        return json.dumps({
            "op": "login",
            "args": [{
                "apiKey": self._api_key,
                "passphrase": self._passphrase,
                "timestamp": ts,
                "sign": self._ws_sign(ts),
            }],
        })

    @staticmethod
    def _build_subscribe_msg() -> str:
        return json.dumps({
            "op": "subscribe",
            "args": [{"channel": "orders", "instType": "SPOT"}],
        })

    # ------------------------------------------------------------------
    # Connection loop with reconnection
    # ------------------------------------------------------------------

    async def _run_loop(self, event_queue: asyncio.Queue) -> None:
        retries = 0

        while self._running:
            try:
                await self._connect_and_stream(event_queue)
                if not self._running:
                    break
                retries = 0

            except (websockets.ConnectionClosed, OSError, asyncio.TimeoutError) as exc:
                if not self._running:
                    break
                retries += 1
                logger.warning(
                    "OKX private WS lost (attempt %d/%d): %s",
                    retries, self.MAX_RETRIES, exc,
                )
                if retries >= self.MAX_RETRIES:
                    await event_queue.put({
                        "type": "status",
                        "exchange": "okx",
                        "connectionStatus": "disconnected",
                    })
                    break
                await event_queue.put({
                    "type": "status",
                    "exchange": "okx",
                    "connectionStatus": "reconnecting",
                })
                delay = self.BACKOFF_DELAYS_S[min(retries - 1, len(self.BACKOFF_DELAYS_S) - 1)]
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                break

            except Exception as exc:
                logger.error("OKX private WS unexpected error: %s", exc, exc_info=True)
                await event_queue.put({
                    "type": "status",
                    "exchange": "okx",
                    "connectionStatus": "disconnected",
                })
                break

    async def _connect_and_stream(self, event_queue: asyncio.Queue) -> None:
        extra_headers = {}
        if self._simulated:
            extra_headers["x-simulated-trading"] = "1"

        async with websockets.connect(self._ws_url, additional_headers=extra_headers) as ws:
            self._ws = ws

            await self._authenticate(ws)
            await self._subscribe_orders(ws)

            await event_queue.put({
                "type": "status",
                "exchange": "okx",
                "connectionStatus": "connected",
            })

            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                async for raw in ws:
                    if raw == "pong":
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if "data" in data and data.get("arg", {}).get("channel") == "orders":
                        for item in data["data"]:
                            event = self._normalize_order_event(item)
                            if event:
                                await event_queue.put(event)
            finally:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

    # ------------------------------------------------------------------
    # Protocol helpers
    # ------------------------------------------------------------------

    async def _authenticate(self, ws) -> None:
        await ws.send(self._build_login_msg())
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if resp.get("event") != "login" or resp.get("code") != "0":
            raise ConnectionError(f"OKX WS login failed: {resp}")

    async def _subscribe_orders(self, ws) -> None:
        await ws.send(self._build_subscribe_msg())
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if resp.get("event") == "error":
            raise ConnectionError(f"OKX WS subscribe failed: {resp}")

    async def _ping_loop(self, ws) -> None:
        try:
            while True:
                await asyncio.sleep(self.PING_INTERVAL_S)
                await ws.send("ping")
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    def _normalize_order_event(self, item: dict) -> dict | None:
        status = OKX_STATE_MAP.get(item.get("state"))
        if not status:
            return None

        inst_id = item.get("instId", "")
        return {
            "type": "order_event",
            "exchange": "okx",
            "pair": self._normalize_pair(inst_id),
            "orderId": item.get("ordId", ""),
            "status": status,
            "side": item.get("side", ""),
            "price": float(item.get("px") or item.get("fillPx") or 0),
            "size": float(item.get("sz") or 0),
            "timestamp": item.get("uTime", ""),
        }
