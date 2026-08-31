"""OKX private order-event stream, routed through the CU Quants Proxy.

Replaces the old hand-rolled `websockets.connect` + OKX `op:"login"`
handshake with `proxy_client.websocket.ProxyWebSocketClient` (`exchange=
"okx"`): the Proxy owns the signed §5.2 handshake and, upstream, OKX's own
private-socket login with the vaulted key. This class subscribes to the
private `orders` channel and normalizes each frame onto the same queue
payload the frontend already consumes — `_normalize_order_event` is
unchanged from the direct implementation.

Reconnection is the SDK's job now (its `default_backoff` supervisor, which
also replays the `orders` subscription). What this class still owns is
translating the connection's up/down transitions into the
`connected` / `reconnecting` / `disconnected` status events the dashboard's
connection indicator reads. That's done by polling `is_connected` once a
second (Option A) — a small, dependency-free stand-in until the SDK grows
`on_connect` / `on_disconnect` hooks.
"""

import asyncio
import logging
from typing import Callable, Optional

from proxy_client.websocket import ProxyWebSocketClient

from exchange_services.proxy_session import ProxySession

logger = logging.getLogger(__name__)

OKX_STATE_MAP = {
    "live": "live",
    "partially_filled": "partially_filled",
    "filled": "filled",
    "canceled": "canceled",
    "mmp_canceled": "canceled",
}

# Exponential backoff (seconds) for the *initial* connect only. Once the
# first connection is up, the SDK's own supervisor owns reconnects.
_INITIAL_CONNECT_BACKOFF_S = [1, 2, 4, 8, 16, 30]
_STATUS_POLL_INTERVAL_S = 1.0


class OkxOrderEventStream:
    """Authenticated order-event stream for OKX via the Proxy.

    Lifecycle: `start(queue)` kicks off a background task that connects and
    begins pushing normalized events into `queue`; `stop()` tears it down.
    `start()` never raises on a connection failure — it retries in the
    background, exactly like the previous implementation.
    """

    def __init__(
        self,
        proxy: ProxySession,
        pair_normalizer: Callable[[str], str] = lambda x: x,
    ):
        self._proxy = proxy
        self._normalize_pair = pair_normalizer
        self._ws: Optional[ProxyWebSocketClient] = None
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, event_queue: asyncio.Queue) -> None:
        if self._task is not None:
            return
        self._queue = event_queue
        self._running = True
        self._ws = ProxyWebSocketClient.for_operator(
            base_url=self._proxy.base_url,
            api_key=self._proxy.api_key,
            secret=self._proxy.secret,
            operator_id=self._proxy.operator_id,
            operator_name=self._proxy.operator_name,
            exchange="okx",
            ws_url=self._proxy.ws_url_override or "",
            on_error=self._on_handler_error,
        )
        self._ws.add_handler("orders", self._on_orders)
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._ws:
            try:
                await self._ws.stop()
            except Exception:
                pass
            self._ws = None
        await self._emit_status("disconnected")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Bring the first connection up (retrying), then watch it."""
        assert self._ws is not None

        attempt = 0
        while self._running:
            try:
                await self._ws.start()
                await self._ws.subscribe("orders", {"instType": "SPOT"})
                break
            except asyncio.CancelledError:
                return
            except Exception as exc:
                attempt += 1
                delay = _INITIAL_CONNECT_BACKOFF_S[
                    min(attempt - 1, len(_INITIAL_CONNECT_BACKOFF_S) - 1)
                ]
                logger.warning(
                    "OKX proxy WS initial connect failed (attempt %d), retrying in %ds: %s",
                    attempt, delay, exc,
                )
                # start() may have half-succeeded (connected, then subscribe
                # raised); reset so the next attempt can call start() again.
                try:
                    await self._ws.stop()
                except Exception:
                    pass
                await self._emit_status("reconnecting")
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return

        if not self._running:
            return

        # Connected. The SDK's supervisor owns reconnects and subscription
        # replay from here; we only surface up/down transitions.
        logger.info("OKX proxy WS connected and subscribed to orders")
        await self._emit_status("connected")

        was_up = True
        while self._running:
            try:
                await asyncio.sleep(_STATUS_POLL_INTERVAL_S)
            except asyncio.CancelledError:
                return
            up = self._ws.is_connected
            if up != was_up:
                await self._emit_status("connected" if up else "reconnecting")
                was_up = up

    # ------------------------------------------------------------------
    # Frame handling
    # ------------------------------------------------------------------

    async def _on_orders(self, msg: dict) -> None:
        """Handler for the private `orders` channel. `msg` is OKX's own
        frame, relayed verbatim: `{"arg": {...}, "data": [ <order>, ... ]}`.
        """
        if self._queue is None:
            return
        for item in msg.get("data", []):
            event = self._normalize_order_event(item)
            if event:
                await self._queue.put(event)

    def _on_handler_error(self, exc: Exception) -> None:
        logger.warning("OKX order-event handler raised: %s", exc)

    def _normalize_order_event(self, item: dict) -> dict | None:
        status = OKX_STATE_MAP.get(item.get("state") or "")
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

    # ------------------------------------------------------------------
    # Status events
    # ------------------------------------------------------------------

    async def _emit_status(self, status: str) -> None:
        if self._queue is None:
            return
        await self._queue.put({
            "type": "status",
            "exchange": "okx",
            "connectionStatus": status,
        })
