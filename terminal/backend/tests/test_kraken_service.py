"""Kraken service unit tests.

These tests mock at the HTTP layer with ``respx`` (intercepts ``httpx``
calls) rather than patching the service's private ``_request`` method.
This lets us assert on the actual URL, method, form-urlencoded body,
and auth headers Kraken sees — catching bugs in HMAC signing, nonce
generation, path construction, and pair normalization.
"""

import os

import httpx
import pytest

from exchange_services.kraken_service import KrakenService
from models import PlaceOrderRequest, TradeResponse


KRAKEN_BASE_URL = "https://api.kraken.com"


# Sample Kraken TradesHistory response (matches /0/private/TradesHistory).
# Kraken uses XXBT=BTC, ZUSD=USD, XETH=ETH; pair format XXBTZUSD.
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


# ---------------------------------------------------------------------------
# get_trades (TradesHistory)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_parses_trades_history_correctly(respx_mock):
    """KrakenService.get_trades parses TradesHistory into TradeResponse list."""
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)

    respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/TradesHistory").mock(
        return_value=httpx.Response(200, json=KRAKEN_TRADES_RESPONSE),
    )

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
    assert t0.fee_currency
    assert t0.role in ("maker", "taker")
    assert t0.timestamp

    # Second trade: XXBTZUSD, sell
    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit(respx_mock):
    """get_trades with pair filter sends ``pair=XETHUSD`` in form body.

    With respx we can verify the full Kraken request: POST method, the
    ``/0/private/TradesHistory`` path, the form-urlencoded body, and
    the presence of HMAC signing headers.
    """
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)

    route = respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/TradesHistory").mock(
        return_value=httpx.Response(
            200,
            json={
                "error": [],
                "result": {
                    "trades": dict(list(KRAKEN_TRADES_RESPONSE["result"]["trades"].items())[:1]),
                    "count": 1,
                },
            },
        ),
    )

    await kraken.get_trades(pair="ETH/USD", limit=5)

    assert route.called
    req = route.calls.last.request
    assert req.method == "POST"
    # Body is form-urlencoded: ``nonce=...&pair=XETHUSD``.
    body = req.content.decode()
    assert "pair=XETHUSD" in body
    assert "nonce=" in body
    # HMAC signing headers must be set.
    assert req.headers.get("API-Key") is not None
    assert req.headers.get("API-Sign") is not None
    assert req.headers.get("content-type", "").startswith("application/x-www-form-urlencoded")


@pytest.mark.asyncio
async def test_get_trades_empty_response(respx_mock):
    """get_trades handles empty trades dict without error."""
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)

    respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/TradesHistory").mock(
        return_value=httpx.Response(200, json={"error": [], "result": {"trades": {}, "count": 0}}),
    )

    trades = await kraken.get_trades()
    assert trades == []


# ---------------------------------------------------------------------------
# Account balance endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance(respx_mock):
    """get_available_cash returns quote currency (ZUSD->USD) balance."""
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "ZUSD": "1234.56",
            "XXBT": "0.5",
        },
    }

    respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/Balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await kraken.get_available_cash("BTC/USD")

    assert result.exchange == "kraken"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen >= 0
    assert result.total == 1234.56


@pytest.mark.asyncio
async def test_get_all_balances_returns_all_currencies(respx_mock):
    """get_all_balances returns all currencies from full balance response."""
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "ZUSD": "1000",
            "XXBT": "0.5",
        },
    }

    respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/Balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await kraken.get_all_balances()

    assert result.exchange == "kraken"
    assert len(result.currencies) == 2
    usd = next(c for c in result.currencies if c.currency == "USD")
    assert usd.available == 1000
    btc = next(c for c in result.currencies if c.currency == "BTC")
    assert btc.available == 0.5


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero(respx_mock):
    """get_all_positions returns only non-zero, non-stablecoin holdings."""
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "ZUSD": "1000",
            "XXBT": "0.5",
            "XETH": "0",
        },
    }

    respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/Balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await kraken.get_all_positions()

    assert result.exchange == "kraken"
    assert len(result.positions) == 1
    assert result.positions[0].currency == "BTC"
    assert result.positions[0].available == 0.5


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance(respx_mock):
    """get_available_positions returns base currency balance.

    Kraken's real /0/private/Balance returns BTC under the legacy
    X-prefixed key ``XXBT`` (not ``XBT``). The mock mirrors that.
    """
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)
    balance_response = {
        "error": [],
        "result": {
            "XXBT": "0.5",
            "ZUSD": "1000",
        },
    }

    respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/Balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await kraken.get_available_positions("BTC/USD")

    assert result.exchange == "kraken"
    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.total >= 0.5


# ---------------------------------------------------------------------------
# place_order error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_returns_error_on_kraken_failure(respx_mock):
    """place_order returns (None, error_msg) when Kraken rejects the order."""
    kraken = KrakenService(base_url=KRAKEN_BASE_URL, simulated=True)
    kraken_response = {
        "error": ["EInsufficient:Insufficient funds"],
        "result": {},
    }

    route = respx_mock.post(f"{KRAKEN_BASE_URL}/0/private/AddOrder").mock(
        return_value=httpx.Response(200, json=kraken_response),
    )

    order, err = await kraken.place_order(
        PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1),
    )

    assert order is None
    assert err is not None
    assert "Insufficient" in err or "funds" in err.lower()

    # Verify request shape.
    assert route.called
    body = route.calls.last.request.content.decode()
    assert "pair=SOLUSD" in body
    assert "type=sell" in body
    assert "ordertype=market" in body


# ---------------------------------------------------------------------------
# Order lifecycle (integration - hits LIVE Kraken API)
# ---------------------------------------------------------------------------
# WARNING: Kraken has no paper-trading sandbox. ``simulated=True`` is a
# no-op on KrakenService today, so this test places a real (but
# intentionally unfillable) order on the live account. It is skipped
# unless KRAKEN_API_KEY and KRAKEN_API_SECRET are explicitly set.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_place_view_cancel_order(kraken_svc: KrakenService):
    """Full order lifecycle: place limit far from market, list, cancel, verify gone."""
    for var in ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"):
        if not os.getenv(var):
            pytest.skip(f"{var} not set; skipping live-API Kraken test")

    order = PlaceOrderRequest(
        pair="BTC/USD",
        side="buy",
        type="limit",
        # Far below any realistic BTC price so the order cannot fill while
        # the test runs. This is the price (in USD) per BTC.
        price=1000,
        size=0.1,
    )
    placed, err = await kraken_svc.place_order(order)
    assert err is None, f"place_order failed: {err}"
    assert placed is not None
    order_id = placed.id

    try:
        pending = await kraken_svc.get_orders(pair="BTC/USD")
        found = [o for o in pending if o.id == order_id]
        assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

        cancelled = await kraken_svc.cancel_order(order_id, "BTC/USD")
        assert cancelled is True, f"cancel_order returned False for order {order_id}"

        pending_after = await kraken_svc.get_orders(pair="BTC/USD")
        still_there = [o for o in pending_after if o.id == order_id]
        assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
    finally:
        # Best-effort cleanup so a failed assertion doesn't leak an open
        # order on the live account between runs.
        try:
            await kraken_svc.cancel_order(order_id, "BTC/USD")
        except Exception:
            pass
