import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException

from models import PlaceOrderRequest, OrderResponse

from auth import current_container, ws_session
from auth.deps import WS_UNAUTHORIZED
from exchange_services.service_container import ServiceContainer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


# ------------------------------------------------------------------
# WebSocket: real-time order events
# ------------------------------------------------------------------

@router.websocket("/{exchange}")
async def order_events_ws(websocket: WebSocket, exchange: str):
    """Frontend connects here to receive normalized order events for an exchange.
    The signed-in trader's own relay starts their private exchange WS on their
    first tab and tears it down on their last. No symbol param — subscription
    is global per-exchange.

    Authenticated by the session cookie (browsers send it on the handshake;
    `ws_session` also checks Origin). Refused sockets are closed with 4401.
    """
    session = await ws_session(websocket)
    await websocket.accept()
    if session is None:
        await websocket.close(code=WS_UNAUTHORIZED, reason="not signed in")
        return
    relay = session.relay
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
async def get_orders(
    exchange: str,
    pair: Optional[str] = Query(None),
    container: ServiceContainer = Depends(current_container),
):
    """Fetch open orders on an exchange: for one normalized pair, or every
    open order on the account when `pair` is omitted."""
    service = container.get_service(exchange)
    return await service.get_orders(pair=pair)


@router.post("/{exchange}", response_model=OrderResponse)
async def place_order(exchange: str, body: PlaceOrderRequest, container: ServiceContainer = Depends(current_container)):
    """Place an order on the given exchange."""
    service = container.get_service(exchange)
    order, error = await service.place_order(body)
    if error:
        logger.warning("Order rejected: exchange=%s pair=%s side=%s error=%s", exchange, body.pair, body.side, error)
        raise HTTPException(status_code=400, detail=error)
    return order


@router.delete("/{exchange}/{order_id}")
async def cancel_order(
    exchange: str,
    order_id: str,
    pair: str = Query(...),
    container: ServiceContainer = Depends(current_container),
):
    """Cancel an order on the given exchange."""
    service = container.get_service(exchange)
    success = await service.cancel_order(order_id, pair)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel order")
    return {"success": True}
