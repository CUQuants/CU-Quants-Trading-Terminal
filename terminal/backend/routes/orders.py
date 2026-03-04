import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Request

from models import PlaceOrderRequest, OrderResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


# ------------------------------------------------------------------
# WebSocket: real-time order events
# ------------------------------------------------------------------

@router.websocket("/{exchange}")
async def order_events_ws(websocket: WebSocket, exchange: str):
    """Frontend connects here to receive normalized order events for an exchange.
    The relay starts the exchange's private WS on first client and tears it
    down on last disconnect. No symbol param — subscription is global per-exchange.
    """
    relay = websocket.app.state.order_event_relay
    await websocket.accept()
    try:
        await relay.register_client(exchange, websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await relay.deregister_client(exchange, websocket)


# ------------------------------------------------------------------
# REST: order CRUD
# ------------------------------------------------------------------

@router.get("/{exchange}", response_model=List[OrderResponse])
async def get_orders(request: Request, exchange: str, pair: str = Query(...)):
    """Fetch open orders for a specific exchange and normalized pair."""
    service = request.app.state.service_container.get_service(exchange)
    return await service.get_orders(pair=pair)


@router.post("/{exchange}", response_model=OrderResponse)
async def place_order(request: Request, exchange: str, body: PlaceOrderRequest):
    """Place an order on the given exchange."""
    service = request.app.state.service_container.get_service(exchange)
    order, error = await service.place_order(body)
    if error:
        logger.warning("Order rejected: exchange=%s pair=%s side=%s error=%s", exchange, body.pair, body.side, error)
        raise HTTPException(status_code=400, detail=error)
    return order


@router.delete("/{exchange}/{order_id}")
async def cancel_order(
    request: Request,
    exchange: str,
    order_id: str,
    pair: str = Query(...),
):
    """Cancel an order on the given exchange."""
    service = request.app.state.service_container.get_service(exchange)
    success = await service.cancel_order(order_id, pair)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel order")
    return {"success": True}
