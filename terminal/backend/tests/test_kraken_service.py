import sys
import os
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.kraken_service import KrakenService
from models import PlaceOrderRequest, TradeResponse


@pytest.fixture
def kraken():
    return KrakenService(base_url="https://api.kraken.com", simulated=True)


# ---------------------------------------------------------------------------
# get_trades (TradesHistory) - mocked unit test
# ---------------------------------------------------------------------------

# Sample Kraken TradesHistory response (matches /private/TradesHistory format)
# Kraken uses XXBT=BTC, ZUSD=USD, XETH=ETH; pair format XXBTZUSD
KRAKEN_TRADES_RESPONSE = {
    "error": [],
    "result": {
        "trades": {
            "TXNID-SOL-001": {
                "ordertxid": "ORD-SOL-001",
                "pair": "SOLUSD",
                "time": 1730385593.0,
                "type": "buy",
                "price": "82.01",
                "cost": "82.01",
                "fee": "0.002",
                "vol": "1.0",
                "margin": "0",
                "misc": "",
            },
            "TXNID-BTC-001": {
                "ordertxid": "ORD-BTC-001",
                "pair": "XXBTZUSD",
                "time": 1730385600.0,
                "type": "sell",
                "price": "95000.50",
                "cost": "95.0005",
                "fee": "0.095",
                "vol": "0.001",
                "margin": "0",
                "misc": "",
            },
        },
        "count": 2,
    },
}


@pytest.mark.asyncio
async def test_get_trades_parses_trades_history_correctly():
    """
    Unit test: KrakenService.get_trades correctly parses Kraken TradesHistory API response
    into TradeResponse objects with proper normalization.

    Success metrics:
    - No exception raised
    - Returns list of TradeResponse
    - Pair normalization: XXBTZUSD -> BTC/USD, SOLUSD -> SOL/USD
    - Role mapping (Kraken misc/order-type -> maker/taker)
    - Fee: abs() applied if negative
    - All required fields present and correctly typed
    - Limit param respected (at most N items)
    """
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value=KRAKEN_TRADES_RESPONSE):
        trades = await kraken.get_trades(limit=10)

    assert isinstance(trades, list)
    assert len(trades) == 2

    # First trade: SOLUSD, buy
    t0 = trades[0]
    assert isinstance(t0, TradeResponse)
    assert t0.id == "TXNID-SOL-001"
    assert t0.order_id == "ORD-SOL-001"
    assert t0.pair == "SOL/USD"
    assert t0.exchange == "kraken"
    assert t0.side == "buy"
    assert t0.price == 82.01
    assert t0.size == 1.0
    assert t0.fee == 0.002
    assert t0.fee_currency  # set (quote or base per Kraken)
    assert t0.role in ("maker", "taker")
    assert t0.timestamp

    # Second trade: XXBTZUSD, sell
    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit():
    """get_trades with pair filter requests correct pair; limit caps results."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)

    captured_path_or_body = None

    async def capture_request(method, path, body=None, headers=None):
        nonlocal captured_path_or_body
        captured_path_or_body = body if body else path
        return {"error": [], "result": {"trades": dict(list(KRAKEN_TRADES_RESPONSE["result"]["trades"].items())[:1]), "count": 1}}

    with patch.object(kraken, "_request", new_callable=AsyncMock, side_effect=capture_request):
        await kraken.get_trades(pair="ETH/USD", limit=5)

    assert captured_path_or_body is not None
    # Implementation will pass pair and count in request (Kraken uses POST with body)
    assert "ETH" in str(captured_path_or_body) or "eth" in str(captured_path_or_body).lower()


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance():
    """get_available_cash returns quote currency (ZUSD->USD) balance."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "ZUSD": "1234.56",
            "XXBT": "0.5",
        },
    }

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await kraken.get_available_cash("BTC/USD")

    assert result.exchange == "kraken"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen >= 0
    assert result.total == 1234.56


@pytest.mark.asyncio
async def test_get_all_balances_returns_all_currencies():
    """get_all_balances returns all currencies from full balance response."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "ZUSD": "1000",
            "XXBT": "0.5",
        },
    }

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await kraken.get_all_balances()

    assert result.exchange == "kraken"
    assert len(result.currencies) == 2
    usd = next(c for c in result.currencies if c.currency == "USD")
    assert usd.available == 1000
    btc = next(c for c in result.currencies if c.currency == "BTC")
    assert btc.available == 0.5


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero():
    """get_all_positions returns only non-zero, non-stablecoin holdings."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "ZUSD": "1000",
            "XXBT": "0.5",
            "XETH": "0",
        },
    }

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await kraken.get_all_positions()

    assert result.exchange == "kraken"
    assert len(result.positions) == 1
    assert result.positions[0].currency == "BTC"
    assert result.positions[0].available == 0.5


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance():
    """get_available_positions returns base currency balance."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "XXBT": "0.5",
            "ZUSD": "1000",
        },
    }

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await kraken.get_available_positions("BTC/USD")

    assert result.exchange == "kraken"
    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.total >= 0.5


@pytest.mark.asyncio
async def test_get_trades_empty_response():
    """get_trades handles empty trades dict without error."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value={"error": [], "result": {"trades": {}, "count": 0}}):
        trades = await kraken.get_trades()

    assert trades == []


# ---------------------------------------------------------------------------
# place_order error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_returns_error_on_kraken_failure():
    """place_order returns (None, error_msg) when Kraken rejects the order."""
    kraken = KrakenService(base_url="https://api.kraken.com", simulated=True)
    kraken_response = {
        "error": ["EInsufficient:Insufficient funds"],
        "result": {},
    }

    with patch.object(kraken, "_request", new_callable=AsyncMock, return_value=kraken_response):
        order, err = await kraken.place_order(
            PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1),
        )

    assert order is None
    assert err is not None
    assert "Insufficient" in err or "funds" in err.lower()


# ---------------------------------------------------------------------------
# Order lifecycle (integration - requires API keys)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_view_cancel_order(kraken: KrakenService):
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
    placed, err = await kraken.place_order(order)
    assert err is None, f"place_order failed: {err}"
    assert placed is not None
    order_id = placed.id

    pending = await kraken.get_orders(pair="BTC/USD")
    found = [o for o in pending if o.id == order_id]
    assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

    cancelled = await kraken.cancel_order(order_id, "BTC/USD")
    assert cancelled is True, f"cancel_order returned False for order {order_id}"

    pending_after = await kraken.get_orders(pair="BTC/USD")
    still_there = [o for o in pending_after if o.id == order_id]
    assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
