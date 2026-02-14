"""
Trading Terminal Backend
FastAPI server that streams Kraken ticker data to frontend clients
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from kraken_client import get_tradable_pairs, get_websocket_pairs
from kraken_ws import KrakenWebSocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Store connected frontend clients
connected_clients: Set[WebSocket] = set()

# Store latest ticker data for each pair
ticker_cache: dict = {}

# All available pairs
all_pairs: list = []

# Kraken WebSocket client instance
kraken_ws: KrakenWebSocket = None


async def broadcast_ticker(ticker: dict) -> None:
    """Broadcast ticker update to all connected frontend clients"""
    ticker_cache[ticker["pair"]] = ticker

    if not connected_clients:
        return

    message = json.dumps({
        "type": "ticker",
        "data": ticker
    })

    # Send to all connected clients
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)

    # Remove disconnected clients
    connected_clients.difference_update(disconnected)


async def start_kraken_connection():
    """Initialize connection to Kraken and subscribe to all pairs"""
    global kraken_ws, all_pairs

    logger.info("Fetching tradable pairs from Kraken...")
    try:
        pairs_data = await get_tradable_pairs()
        all_pairs = get_websocket_pairs(pairs_data)
        logger.info(f"Found {len(all_pairs)} tradable pairs")

        # Create Kraken WebSocket client
        kraken_ws = KrakenWebSocket(on_ticker_update=broadcast_ticker)

        # Start connection in background task
        asyncio.create_task(kraken_ws.connect())

        # Wait a moment for connection to establish
        await asyncio.sleep(2)

        # Subscribe to all pairs
        logger.info(f"Subscribing to ticker updates for {len(all_pairs)} pairs...")
        await kraken_ws.subscribe(all_pairs)

    except Exception as e:
        logger.error(f"Failed to initialize Kraken connection: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    await start_kraken_connection()

    # Start heartbeat task
    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            if kraken_ws:
                await kraken_ws.ping()

    heartbeat_task = asyncio.create_task(heartbeat())

    yield

    # Shutdown
    heartbeat_task.cancel()
    if kraken_ws:
        await kraken_ws.close()


app = FastAPI(
    title="Trading Terminal Backend",
    description="WebSocket server for Kraken market data",
    lifespan=lifespan
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "pairs_count": len(all_pairs),
        "connected_clients": len(connected_clients),
        "cached_tickers": len(ticker_cache)
    }


@app.get("/pairs")
async def get_pairs():
    """Get all available trading pairs"""
    return {
        "pairs": all_pairs,
        "count": len(all_pairs)
    }


@app.get("/tickers")
async def get_tickers():
    """Get all cached ticker data"""
    return {
        "tickers": ticker_cache,
        "count": len(ticker_cache)
    }


@app.get("/ticker/{pair}")
async def get_ticker(pair: str):
    """Get ticker data for a specific pair"""
    if pair in ticker_cache:
        return ticker_cache[pair]
    return {"error": f"No ticker data for {pair}"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for frontend clients.
    Streams all ticker updates in real-time.
    """
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Client connected. Total clients: {len(connected_clients)}")

    try:
        # Send initial data: all available pairs and cached tickers
        await websocket.send_text(json.dumps({
            "type": "init",
            "data": {
                "pairs": all_pairs,
                "tickers": ticker_cache
            }
        }))

        # Keep connection alive and handle client messages
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60
                )

                # Handle client messages (e.g., subscribe to specific pairs)
                data = json.loads(message)

                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif data.get("type") == "subscribe":
                    # Client wants specific pairs only
                    pairs = data.get("pairs", [])
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "pairs": pairs
                    }))

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({"type": "ping"}))

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Client removed. Total clients: {len(connected_clients)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
