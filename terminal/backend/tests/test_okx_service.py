import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.okx_service import OkxService
from models import Order


@pytest.fixture
def okx():
    return OkxService(base_url="https://us.okx.com", simulated=True)


@pytest.mark.asyncio
async def test_place_view_cancel_order(okx: OkxService):
    """
    Full order lifecycle: place a limit order far from market price,
    verify it appears in pending orders, cancel it, then verify it's gone.
    """

    # 1. Place a limit buy well below market price so it stays open
    order = Order(
        symbol="BTC/USD",
        exchange="okx",
        quantity=1,
        price=1000.00,
        side="buy",
        order_type="limit",
    )
    placed = await okx.place_order(order)
    assert placed.id is not None
    order_id = placed.id

    # 2. Verify it shows up in pending orders
    pending = await okx.get_orders()
    found = [o for o in pending if o.id == order_id]
    assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

    # 3. Cancel the order
    cancelled = await okx.cancel_order(order_id, "BTC/USD")
    assert cancelled is True, f"cancel_order returned False for order {order_id}"

    # 4. Verify it's gone from pending orders
    pending_after = await okx.get_orders()
    still_there = [o for o in pending_after if o.id == order_id]
    assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
