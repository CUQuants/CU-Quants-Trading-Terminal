"""
Kraken WebSocket Client
Connects to Kraken public WebSocket and streams ticker data
"""

import asyncio
import json
import logging
from typing import Callable, List, Set, Optional
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)

KRAKEN_WS_PUBLIC = "wss://ws.kraken.com"


class KrakenWebSocket:
    def __init__(self, on_ticker_update: Callable):
        self.ws: Optional[WebSocketClientProtocol] = None
        self.on_ticker_update = on_ticker_update
        self.subscribed_pairs: Set[str] = set()
        self._running = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 30

    async def connect(self) -> None:
        """Establish WebSocket connection to Kraken"""
        self._running = True
        while self._running:
            try:
                logger.info(f"Connecting to Kraken WebSocket: {KRAKEN_WS_PUBLIC}")
                async with websockets.connect(KRAKEN_WS_PUBLIC) as ws:
                    self.ws = ws
                    self._reconnect_delay = 1  # Reset on successful connection
                    logger.info("Connected to Kraken WebSocket")

                    # Resubscribe to pairs if we had any
                    if self.subscribed_pairs:
                        await self._send_subscription(list(self.subscribed_pairs))

                    await self._listen()
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )

    async def _listen(self) -> None:
        """Listen for incoming WebSocket messages"""
        async for message in self.ws:
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")

    async def _handle_message(self, data) -> None:
        """Process incoming WebSocket messages"""
        # System messages (dicts)
        if isinstance(data, dict):
            event = data.get("event")

            if event == "heartbeat":
                return

            if event == "systemStatus":
                logger.info(f"Kraken system status: {data.get('status')}")
                return

            if event == "subscriptionStatus":
                status = data.get("status")
                if status == "subscribed":
                    logger.info(f"Subscribed to {data.get('channelName')} for {data.get('pair')}")
                elif status == "error":
                    logger.error(f"Subscription error: {data.get('errorMessage')}")
                return

            if event == "pong":
                return

            logger.debug(f"System event: {event}")
            return

        # Data messages (arrays): [channelID, data, channelName, pair]
        if isinstance(data, list) and len(data) >= 4:
            channel_id, ticker_data, channel_name, pair = data

            if channel_name == "ticker":
                await self._handle_ticker(pair, ticker_data)

    async def _handle_ticker(self, pair: str, data: dict) -> None:
        """Process ticker update and forward to callback"""
        try:
            # Parse Kraken ticker format
            ticker = {
                "pair": pair,
                "bid": data["b"][0],
                "ask": data["a"][0],
                "last": data["c"][0],
                "volume": data["v"][1],  # 24h volume
                "high": data["h"][1],    # 24h high
                "low": data["l"][1],     # 24h low
                "open": data["o"][1],    # Today's open (can be used for change calc)
                "vwap": data["p"][1],    # 24h vwap
            }

            # Calculate change
            last = float(ticker["last"])
            open_price = float(ticker["open"])
            ticker["change"] = str(last - open_price)
            ticker["changePercent"] = str(((last - open_price) / open_price) * 100) if open_price != 0 else "0"

            await self.on_ticker_update(ticker)
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse ticker for {pair}: {e}")

    async def subscribe(self, pairs: List[str]) -> None:
        """Subscribe to ticker updates for given pairs"""
        if not pairs:
            return

        # Kraken limits subscriptions to ~50 pairs per message
        batch_size = 50
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            self.subscribed_pairs.update(batch)

            if self.ws and self.ws.open:
                await self._send_subscription(batch)

    async def _send_subscription(self, pairs: List[str]) -> None:
        """Send subscription message to Kraken"""
        subscription = {
            "event": "subscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"}
        }
        logger.info(f"Subscribing to {len(pairs)} pairs")
        await self.ws.send(json.dumps(subscription))

    async def unsubscribe(self, pairs: List[str]) -> None:
        """Unsubscribe from ticker updates"""
        if not self.ws or not self.ws.open:
            return

        unsubscription = {
            "event": "unsubscribe",
            "pair": pairs,
            "subscription": {"name": "ticker"}
        }
        await self.ws.send(json.dumps(unsubscription))
        self.subscribed_pairs.difference_update(pairs)

    async def ping(self) -> None:
        """Send ping to keep connection alive"""
        if self.ws and self.ws.open:
            await self.ws.send(json.dumps({"event": "ping"}))

    async def close(self) -> None:
        """Close the WebSocket connection"""
        self._running = False
        if self.ws:
            await self.ws.close()
