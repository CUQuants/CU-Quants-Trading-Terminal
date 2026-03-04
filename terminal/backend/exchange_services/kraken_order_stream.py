import asyncio
import json
import logging
from typing import Callable, Sequence

import websockets

logger = logging.getLogger(__name__)


class KrakenOrderEventStream:
    """Public WebSocket v2 connection to Kraken.

    This class mirrors the OkxOrderEventStream lifecycle so it can plug into the
    same relay. Because it uses only public WS v2 (`wss://ws.kraken.com/v2`),
    it can publish connection status and market-driven synthetic events, but it
    cannot stream true account order lifecycle updates.
    """

    WS_URL = "wss://ws.kraken.com/v2"
    PING_INTERVAL_S = 25
    MAX_RETRIES = 3
    BACKOFF_DELAYS_S = [1, 2, 4]

    def __init__(
        self,
        symbols: Sequence[str] | None = None,
        pair_normalizer: Callable[[str], str] = lambda x: x,
    ):
        # Public ticker channel requires at least one symbol.
        self._symbols = list(symbols) if symbols else ["BTC/USD"]
        self._normalize_pair = pair_normalizer
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._req_id = 0

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
                    "Kraken public WS lost (attempt %d/%d): %s",
                    retries,
                    self.MAX_RETRIES,
                    exc,
                )
                if retries >= self.MAX_RETRIES:
                    await event_queue.put({
                        "type": "status",
                        "exchange": "kraken",
                        "connectionStatus": "disconnected",
                    })
                    break

                await event_queue.put({
                    "type": "status",
                    "exchange": "kraken",
                    "connectionStatus": "reconnecting",
                })
                delay = self.BACKOFF_DELAYS_S[min(retries - 1, len(self.BACKOFF_DELAYS_S) - 1)]
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                break

            except Exception as exc:
                logger.error("Kraken public WS unexpected error: %s", exc, exc_info=True)
                await event_queue.put({
                    "type": "status",
                    "exchange": "kraken",
                    "connectionStatus": "disconnected",
                })
                break

    async def _connect_and_stream(self, event_queue: asyncio.Queue) -> None:
        async with websockets.connect(self.WS_URL) as ws:
            self._ws = ws

            await self._subscribe_ticker(ws)
            await event_queue.put({
                "type": "status",
                "exchange": "kraken",
                "connectionStatus": "connected",
            })

            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    # Public status/heartbeat/pong messages are useful for
                    # liveness, but not order lifecycle.
                    if data.get("method") == "pong":
                        continue

                    if data.get("channel") == "ticker":
                        for item in data.get("data", []):
                            event = self._normalize_ticker_to_synthetic_event(item)
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

    async def _subscribe_ticker(self, ws) -> None:
        self._req_id += 1
        msg = {
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": self._symbols,
                "event_trigger": "trades",
                "snapshot": True,
            },
            "req_id": self._req_id,
        }
        await ws.send(json.dumps(msg))

        # Wait for subscribe ack; ignore unrelated status/heartbeat messages.
        deadline = asyncio.get_running_loop().time() + 10
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for Kraken WS subscribe ack")

            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
            if resp.get("method") != "subscribe":
                continue
            if not resp.get("success", False):
                raise ConnectionError(f"Kraken WS subscribe failed: {resp}")
            return

    async def _ping_loop(self, ws) -> None:
        try:
            while True:
                await asyncio.sleep(self.PING_INTERVAL_S)
                self._req_id += 1
                await ws.send(json.dumps({"method": "ping", "req_id": self._req_id}))
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    def _normalize_ticker_to_synthetic_event(self, item: dict) -> dict | None:
        symbol = item.get("symbol")
        if not symbol:
            return None

        price = self._coerce_float(item.get("last"), "price")
        if price == 0:
            price = self._coerce_float(item.get("bid"), "price")
        if price == 0:
            price = self._coerce_float(item.get("ask"), "price")

        size = self._coerce_float(item.get("volume"), "qty")
        if size == 0:
            size = self._coerce_float(item.get("bid_qty"), "qty")
        if size == 0:
            size = self._coerce_float(item.get("ask_qty"), "qty")

        # Public ticker feed has no account order identifiers or state.
        # Emit a synthetic event shape to keep downstream handling uniform.
        return {
            "type": "order_event",
            "exchange": "kraken",
            "pair": self._normalize_pair(symbol),
            "orderId": f"public-ticker:{symbol}",
            "status": "live",
            "side": "buy",
            "price": price,
            "size": size,
            "timestamp": item.get("timestamp", ""),
        }

    @staticmethod
    def _coerce_float(value, nested_key: str | None = None) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float, str)):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        if isinstance(value, dict):
            if nested_key and nested_key in value:
                return KrakenOrderEventStream._coerce_float(value[nested_key], None)
            for candidate in ("price", "qty", "value"):
                if candidate in value:
                    return KrakenOrderEventStream._coerce_float(value[candidate], None)
        return 0.0
