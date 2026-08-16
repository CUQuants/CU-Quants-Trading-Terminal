"""
Base class for exchange order event streams.

Provides shared lifecycle (start/stop), retry-with-backoff logic, and status event emission.
Subclasses implement _connect_and_stream to handle exchange-specific connection and parsing.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Literal

import websockets

logger = logging.getLogger(__name__)

ConnectionStatus = Literal["connected", "reconnecting", "disconnected"]


class BaseOrderEventStream(ABC):
    """
    Base class for streaming real-time order events from exchange private WebSocket APIs.

    Lifecycle: start() opens the connection and pushes normalized events into the queue.
    stop() tears it down. Reconnects automatically with exponential backoff on failures.
    """

    MAX_RETRIES = 3
    BACKOFF_DELAYS_S = [1, 2, 4]

    def __init__(self, exchange_name: str):
        self._exchange_name = exchange_name
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False

    @abstractmethod
    async def _connect_and_stream(self, event_queue: asyncio.Queue) -> None:
        """
        Connect to the exchange WebSocket, authenticate, subscribe to order events,
        and stream normalized events into event_queue until connection closes or _running is False.

        Subclasses implement exchange-specific logic. May raise ConnectionClosed, OSError,
        TimeoutError on connection loss; the base _run_loop will retry with backoff.
        """
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, event_queue: asyncio.Queue) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(event_queue))

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _emit_status(self, event_queue: asyncio.Queue, status: ConnectionStatus) -> None:
        """Emit a status event to the queue."""
        event_queue.put_nowait({
            "type": "status",
            "exchange": self._exchange_name,
            "connectionStatus": status,
        })

    async def _emit_status_async(self, event_queue: asyncio.Queue, status: ConnectionStatus) -> None:
        """Emit a status event to the queue (async put for use in async context)."""
        await event_queue.put({
            "type": "status",
            "exchange": self._exchange_name,
            "connectionStatus": status,
        })

    async def _run_loop(self, event_queue: asyncio.Queue) -> None:
        """Retry loop: connect, stream until failure, backoff, repeat. Emits status events."""
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
                    "%s private WS lost (attempt %d/%d): %s",
                    self._exchange_name, retries, self.MAX_RETRIES, exc,
                )
                if retries >= self.MAX_RETRIES:
                    await self._emit_status_async(event_queue, "disconnected")
                    break
                await self._emit_status_async(event_queue, "reconnecting")
                delay = self.BACKOFF_DELAYS_S[min(retries - 1, len(self.BACKOFF_DELAYS_S) - 1)]
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                break

            except Exception as exc:
                logger.error(
                    "%s private WS unexpected error: %s", self._exchange_name, exc, exc_info=True
                )
                await self._emit_status_async(event_queue, "disconnected")
                break
