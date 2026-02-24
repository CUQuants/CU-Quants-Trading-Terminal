import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from exchange_services.service_container import ServiceContainer

logger = logging.getLogger(__name__)


class OrderEventRelay:
    """Bridges exchange private WebSocket streams to frontend clients.

    - Maintains a registry of connected frontend WebSocket clients per exchange.
    - Reference-counted: opens an exchange's private WS on first client,
      tears it down when the last client disconnects.
    - Fan-out: every event from the exchange stream is forwarded to all
      registered frontend clients for that exchange.
    - Status events (connected / reconnecting / disconnected) are also relayed.
    """

    def __init__(self, service_container: ServiceContainer):
        self._service_container = service_container
        self._clients: Dict[str, Set[WebSocket]] = {}
        self._event_queues: Dict[str, asyncio.Queue] = {}
        self._fan_out_tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # Client registration (called from the WS route handler)
    # ------------------------------------------------------------------

    async def register_client(self, exchange: str, ws: WebSocket) -> None:
        if exchange not in self._clients:
            self._clients[exchange] = set()

        is_first = len(self._clients[exchange]) == 0
        self._clients[exchange].add(ws)

        if is_first:
            await self._start_exchange_stream(exchange)

    async def deregister_client(self, exchange: str, ws: WebSocket) -> None:
        clients = self._clients.get(exchange)
        if not clients:
            return

        clients.discard(ws)

        if len(clients) == 0:
            await self._stop_exchange_stream(exchange)
            del self._clients[exchange]

    # ------------------------------------------------------------------
    # Exchange stream lifecycle
    # ------------------------------------------------------------------

    async def _start_exchange_stream(self, exchange: str) -> None:
        try:
            service = self._service_container.get_service(exchange)
        except ValueError:
            return
        queue: asyncio.Queue = asyncio.Queue()
        self._event_queues[exchange] = queue

        await service.start_order_stream(queue)

        self._fan_out_tasks[exchange] = asyncio.create_task(
            self._fan_out_loop(exchange, queue)
        )
        logger.info("Started order event stream for exchange: %s", exchange)

    async def _stop_exchange_stream(self, exchange: str) -> None:
        task = self._fan_out_tasks.pop(exchange, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        service = self._service_container.get_service(exchange)
        await service.stop_order_stream()
        self._event_queues.pop(exchange, None)
        logger.info("Stopped order event stream for exchange: %s", exchange)

    # ------------------------------------------------------------------
    # Fan-out: read from queue, broadcast to all clients for that exchange
    # ------------------------------------------------------------------

    async def _fan_out_loop(self, exchange: str, queue: asyncio.Queue) -> None:
        try:
            while True:
                event = await queue.get()
                message = json.dumps(event)

                clients = self._clients.get(exchange, set()).copy()
                stale: list[WebSocket] = []

                for ws in clients:
                    try:
                        if ws.client_state == WebSocketState.CONNECTED:
                            await ws.send_text(message)
                    except Exception:
                        stale.append(ws)

                for ws in stale:
                    await self.deregister_client(exchange, ws)
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Shutdown (called from app lifespan teardown)
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        for exchange in list(self._fan_out_tasks.keys()):
            await self._stop_exchange_stream(exchange)
        self._clients.clear()
        logger.info("OrderEventRelay shut down")
