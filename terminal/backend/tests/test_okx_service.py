import sys
import os
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.okx_service import OkxService
from models import PlaceOrderRequest, TradeResponse


@pytest.fixture
def okx():
    return OkxService(base_url="https://us.okx.com", simulated=True)


# ---------------------------------------------------------------------------
# get_trades (fills-history) - mocked unit test
# ---------------------------------------------------------------------------

# Sample OKX fills-history response (matches /api/v5/trade/fills-history format)
OKX_FILLS_RESPONSE = {
    "code": "0",
    "msg": "",
    "data": [
        {
            "instType": "SPOT",
            "instId": "SOL-USDT",
            "tradeId": "123456789",
            "ordId": "987654321",
            "fillPx": "82.01",
            "fillSz": "1.0",
            "side": "buy",
            "execType": "M",
            "fee": "-0.002",
            "feeCcy": "SOL",
            "fillTime": "1730385593000",
            "ts": "1730385593000",
        },
        {
            "instType": "SPOT",
            "instId": "BTC-USDT",
            "tradeId": "111222333",
            "ordId": "444555666",
            "fillPx": "95000.50",
            "fillSz": "0.001",
            "side": "sell",
            "execType": "T",
            "fee": "0.095",
            "feeCcy": "USDT",
            "fillTime": "1730385600000",
            "ts": "1730385600000",
        },
    ],
}


@pytest.mark.asyncio
async def test_get_trades_parses_fills_history_correctly():
    """
    Unit test: OkxService.get_trades correctly parses OKX fills-history API response
    into TradeResponse objects with proper normalization.

    Success metrics:
    - No exception raised
    - Returns list of TradeResponse
    - Pair normalization: BTC-USDT -> BTC/USD, SOL-USDT -> SOL/USD
    - Role mapping: execType M -> maker, T -> taker
    - Fee: abs() applied (negative fee becomes positive)
    - All required fields present and correctly typed
    - Limit param respected (at most N items)
    """
    okx = OkxService(base_url="https://us.okx.com", simulated=True)

    with patch.object(okx, "_request", new_callable=AsyncMock, return_value=OKX_FILLS_RESPONSE):
        trades = await okx.get_trades(limit=10)

    assert isinstance(trades, list)
    assert len(trades) == 2

    # First trade: SOL-USDT, maker, negative fee
    t0 = trades[0]
    assert isinstance(t0, TradeResponse)
    assert t0.id == "123456789"
    assert t0.order_id == "987654321"
    assert t0.pair == "SOL/USD"
    assert t0.exchange == "okx"
    assert t0.side == "buy"
    assert t0.price == 82.01
    assert t0.size == 1.0
    assert t0.fee == 0.002  # abs() applied
    assert t0.fee_currency == "SOL"
    assert t0.role == "maker"
    assert t0.timestamp == "1730385593000"

    # Second trade: BTC-USDT, taker
    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.role == "taker"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit():
    """get_trades with pair filter requests correct instId; limit caps results."""
    okx = OkxService(base_url="https://us.okx.com", simulated=True)

    captured_path = None

    async def capture_request(method, path, body=None, headers=None):
        nonlocal captured_path
        captured_path = path
        return {"code": "0", "data": OKX_FILLS_RESPONSE["data"][:1]}

    with patch.object(okx, "_request", new_callable=AsyncMock, side_effect=capture_request):
        await okx.get_trades(pair="ETH/USD", limit=5)

    assert "instId=ETH-USDT" in captured_path
    assert "limit=5" in captured_path


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance():
    """get_available_cash returns quote currency (USDT->USD) balance."""
    okx = OkxService(base_url="https://us.okx.com", simulated=True)
    balance_response = {
        "code": "0",
        "data": [{
            "details": [{
                "ccy": "USDT",
                "availBal": "1234.56",
                "frozenBal": "100.00",
                "eq": "1334.56",
            }],
        }],
    }

    with patch.object(okx, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await okx.get_available_cash("BTC/USD")

    assert result.exchange == "okx"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen == 100.0
    assert result.total == 1334.56


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance():
    """get_available_positions returns base currency balance."""
    okx = OkxService(base_url="https://us.okx.com", simulated=True)
    balance_response = {
        "code": "0",
        "data": [{
            "details": [{
                "ccy": "BTC",
                "availBal": "0.5",
                "frozenBal": "0.1",
                "eq": "0.6",
            }],
        }],
    }

    with patch.object(okx, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await okx.get_available_positions("BTC/USD")

    assert result.exchange == "okx"
    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.frozen == 0.1
    assert result.total == 0.6


@pytest.mark.asyncio
async def test_get_trades_empty_response():
    """get_trades handles empty data array without error."""
    okx = OkxService(base_url="https://us.okx.com", simulated=True)

    with patch.object(okx, "_request", new_callable=AsyncMock, return_value={"code": "0", "data": []}):
        trades = await okx.get_trades()

    assert trades == []


# ---------------------------------------------------------------------------
# Order lifecycle (integration - requires API keys)
# ---------------------------------------------------------------------------


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
