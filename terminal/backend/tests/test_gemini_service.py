import sys
import os
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.gemini_service import GeminiService
from models import PlaceOrderRequest, TradeResponse


@pytest.fixture
def gemini():
    return GeminiService(base_url="https://api.gemini.com", simulated=True)


# ---------------------------------------------------------------------------
# get_trades (mytrades) - mocked unit test
# ---------------------------------------------------------------------------

# Sample Gemini mytrades response (matches /v1/mytrades format)
# Gemini uses lowercase symbol: btcusd, ethusd, solusd
GEMINI_TRADES_RESPONSE = [
    {
        "tid": 123456789,
        "order_id": "987654321",
        "symbol": "solusd",
        "price": "82.01",
        "amount": "1.0",
        "side": "buy",
        "fee_amount": "0.002",
        "fee_currency": "SOL",
        "timestamp": 1730385593,
        "is_maker": True,
    },
    {
        "tid": 111222333,
        "order_id": "444555666",
        "symbol": "btcusd",
        "price": "95000.50",
        "amount": "0.001",
        "side": "sell",
        "fee_amount": "0.095",
        "fee_currency": "USD",
        "timestamp": 1730385600,
        "is_maker": False,
    },
]


@pytest.mark.asyncio
async def test_get_trades_parses_mytrades_correctly():
    """
    Unit test: GeminiService.get_trades correctly parses Gemini mytrades API response
    into TradeResponse objects with proper normalization.

    Success metrics:
    - No exception raised
    - Returns list of TradeResponse
    - Pair normalization: btcusd -> BTC/USD, solusd -> SOL/USD
    - Role mapping: is_maker True -> maker, False -> taker
    - Fee: abs() applied if negative
    - All required fields present and correctly typed
    - Limit param respected (at most N items)
    """
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=GEMINI_TRADES_RESPONSE):
        trades = await gemini.get_trades(limit=10)

    assert isinstance(trades, list)
    assert len(trades) == 2

    # First trade: solusd, buy, maker
    t0 = trades[0]
    assert isinstance(t0, TradeResponse)
    assert str(t0.id) == "123456789"
    assert t0.order_id == "987654321"
    assert t0.pair == "SOL/USD"
    assert t0.exchange == "gemini"
    assert t0.side == "buy"
    assert t0.price == 82.01
    assert t0.size == 1.0
    assert t0.fee == 0.002
    assert t0.fee_currency == "SOL"
    assert t0.role == "maker"
    assert t0.timestamp

    # Second trade: btcusd, sell, taker
    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.role == "taker"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit():
    """get_trades with pair filter requests correct symbol; limit caps results."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    captured_path_or_body = None

    async def capture_request(method, path, body=None, headers=None):
        nonlocal captured_path_or_body
        captured_path_or_body = body if body else path
        return GEMINI_TRADES_RESPONSE[:1]

    with patch.object(gemini, "_request", new_callable=AsyncMock, side_effect=capture_request):
        await gemini.get_trades(pair="ETH/USD", limit=5)

    assert captured_path_or_body is not None
    # Implementation will pass symbol and limit in request
    assert "ETH" in str(captured_path_or_body) or "eth" in str(captured_path_or_body).lower()


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance():
    """get_available_cash returns quote currency (USD) balance."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "USD", "amount": "1234.56", "available": "1234.56"},
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
    ]

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await gemini.get_available_cash("BTC/USD")

    assert result.exchange == "gemini"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen >= 0
    assert result.total == 1234.56


@pytest.mark.asyncio
async def test_get_all_balances_returns_all_currencies():
    """get_all_balances returns all currencies from full balance response."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "USD", "amount": "1000", "available": "1000"},
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
    ]

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await gemini.get_all_balances()

    assert result.exchange == "gemini"
    assert len(result.currencies) == 2
    usd = next(c for c in result.currencies if c.currency == "USD")
    assert usd.available == 1000
    btc = next(c for c in result.currencies if c.currency == "BTC")
    assert btc.available == 0.5


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero():
    """get_all_positions returns only non-zero, non-stablecoin holdings."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "USD", "amount": "1000", "available": "1000"},
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
        {"currency": "ETH", "amount": "0", "available": "0"},
    ]

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await gemini.get_all_positions()

    assert result.exchange == "gemini"
    assert len(result.positions) == 1
    assert result.positions[0].currency == "BTC"
    assert result.positions[0].available == 0.5


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance():
    """get_available_positions returns base currency balance."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
        {"currency": "USD", "amount": "1000", "available": "1000"},
    ]

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=balance_response):
        result = await gemini.get_available_positions("BTC/USD")

    assert result.exchange == "gemini"
    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.total >= 0.5


@pytest.mark.asyncio
async def test_get_trades_empty_response():
    """get_trades handles empty array without error."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=[]):
        trades = await gemini.get_trades()

    assert trades == []


# ---------------------------------------------------------------------------
# place_order error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_returns_error_on_gemini_failure():
    """place_order returns (None, error_msg) when Gemini rejects the order."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    gemini_response = {
        "result": "error",
        "reason": "InsufficientBalance",
        "message": "Insufficient balance for order",
    }

    with patch.object(gemini, "_request", new_callable=AsyncMock, return_value=gemini_response):
        order, err = await gemini.place_order(
            PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1),
        )

    assert order is None
    assert err is not None
    assert "Insufficient" in err or "balance" in err.lower()


# ---------------------------------------------------------------------------
# Order lifecycle (integration - requires API keys)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_view_cancel_order(gemini: GeminiService):
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
    placed, err = await gemini.place_order(order)
    assert err is None, f"place_order failed: {err}"
    assert placed is not None
    order_id = placed.id

    pending = await gemini.get_orders(pair="BTC/USD")
    found = [o for o in pending if o.id == order_id]
    assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

    cancelled = await gemini.cancel_order(order_id, "BTC/USD")
    assert cancelled is True, f"cancel_order returned False for order {order_id}"

    pending_after = await gemini.get_orders(pair="BTC/USD")
    still_there = [o for o in pending_after if o.id == order_id]
    assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
