import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.okx_service import OkxService
from models import PlaceOrderRequest


@pytest.fixture
def okx():
    return OkxService(base_url="https://us.okx.com", simulated=True)


@pytest.mark.asyncio
async def test_place_view_cancel_order(okx: OkxService):
    """
    Full order lifecycle: place a limit order far from market price,
    verify it appears in pending orders, cancel it, then verify it's gone.
    """

    order = PlaceOrderRequest(
        pair="BTC/USD",
        side="buy",
        type="limit",
        price=1000.00,
        size=1,
    )
    placed = await okx.place_order(order)
    assert placed.id is not None
    order_id = placed.id

    pending = await okx.get_orders(pair="BTC/USD")
    found = [o for o in pending if o.id == order_id]
    assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

    cancelled = await okx.cancel_order(order_id, "BTC/USD")
    assert cancelled is True, f"cancel_order returned False for order {order_id}"

    pending_after = await okx.get_orders(pair="BTC/USD")
    still_there = [o for o in pending_after if o.id == order_id]
    assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
