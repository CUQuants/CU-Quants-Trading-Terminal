"""OKX service unit tests.

These tests mock at the HTTP layer with ``respx`` (intercepts ``httpx``
calls) rather than patching the service's private ``_request`` method.
This lets us assert on the actual URL, method, query string, and
headers the service emits — which catches bugs in URL construction,
auth signing, and request routing that ``patch.object(_, "_request",
...)`` cannot detect.
"""

import os

import httpx
import pytest

from exchange_services.okx_service import OkxService
from models import PlaceOrderRequest, TradeResponse


OKX_BASE_URL = "https://us.okx.com"


# Sample OKX fills-history response (matches /api/v5/trade/fills-history format).
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


# ---------------------------------------------------------------------------
# get_trades (fills-history)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_parses_fills_history_correctly(respx_mock):
    """OkxService.get_trades parses fills-history into TradeResponse list."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)

    respx_mock.get(f"{OKX_BASE_URL}/api/v5/trade/fills-history").mock(
        return_value=httpx.Response(200, json=OKX_FILLS_RESPONSE),
    )

    trades = await okx.get_trades(limit=10)

    assert isinstance(trades, list)
    assert len(trades) == 2

    t0 = trades[0]
    assert isinstance(t0, TradeResponse)
    assert t0.id == "123456789"
    assert t0.order_id == "987654321"
    assert t0.pair == "SOL/USD"
    assert t0.exchange == "okx"
    assert t0.side == "buy"
    assert t0.price == 82.01
    assert t0.size == 1.0
    assert t0.fee == 0.002
    assert t0.fee_currency == "SOL"
    assert t0.role == "maker"
    assert t0.timestamp == "1730385593000"

    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.role == "taker"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit(respx_mock):
    """get_trades with pair filter requests correct instId; limit caps results.

    With respx we can inspect the actual outbound URL — query string,
    auth headers, and simulated-trading flag — not just whether some
    substring made it into a captured argument.
    """
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)

    route = respx_mock.get(f"{OKX_BASE_URL}/api/v5/trade/fills-history").mock(
        return_value=httpx.Response(200, json={"code": "0", "data": OKX_FILLS_RESPONSE["data"][:1]}),
    )

    await okx.get_trades(pair="ETH/USD", limit=5)

    assert route.called
    req = route.calls.last.request
    assert req.method == "GET"
    query = req.url.query.decode()
    assert "instId=ETH-USDT" in query
    assert "limit=5" in query
    assert "instType=SPOT" in query
    # Signing / auth headers must be present.
    assert req.headers.get("OK-ACCESS-KEY") is not None
    assert req.headers.get("OK-ACCESS-SIGN")
    assert req.headers.get("OK-ACCESS-PASSPHRASE") is not None
    assert req.headers.get("x-simulated-trading") == "1"


@pytest.mark.asyncio
async def test_get_trades_empty_response(respx_mock):
    """get_trades handles empty data array without error."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)

    respx_mock.get(f"{OKX_BASE_URL}/api/v5/trade/fills-history").mock(
        return_value=httpx.Response(200, json={"code": "0", "data": []}),
    )

    trades = await okx.get_trades()
    assert trades == []


# ---------------------------------------------------------------------------
# Account balance endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance(respx_mock):
    """get_available_cash returns quote currency (USDT->USD) balance."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)
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

    respx_mock.get(f"{OKX_BASE_URL}/api/v5/account/balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await okx.get_available_cash("BTC/USD")

    assert result.exchange == "okx"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen == 100.0
    assert result.total == 1334.56


@pytest.mark.asyncio
async def test_get_all_balances_returns_all_currencies(respx_mock):
    """get_all_balances returns all currencies from full balance response."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)
    balance_response = {
        "code": "0",
        "data": [{
            "details": [
                {"ccy": "USDT", "availBal": "1000", "frozenBal": "0", "eq": "1000"},
                {"ccy": "BTC", "availBal": "0.5", "frozenBal": "0.1", "eq": "0.6"},
            ],
        }],
    }

    respx_mock.get(f"{OKX_BASE_URL}/api/v5/account/balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await okx.get_all_balances()

    assert result.exchange == "okx"
    assert len(result.currencies) == 2
    usd = next(c for c in result.currencies if c.currency == "USD")
    assert usd.available == 1000
    btc = next(c for c in result.currencies if c.currency == "BTC")
    assert btc.available == 0.5
    assert btc.frozen == 0.1


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero(respx_mock):
    """get_all_positions returns only non-zero, non-stablecoin holdings."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)
    balance_response = {
        "code": "0",
        "data": [{
            "details": [
                {"ccy": "USDT", "availBal": "1000", "frozenBal": "0", "eq": "1000"},
                {"ccy": "BTC", "availBal": "0.5", "frozenBal": "0", "eq": "0.5"},
                {"ccy": "ETH", "availBal": "0", "frozenBal": "0", "eq": "0"},
            ],
        }],
    }

    respx_mock.get(f"{OKX_BASE_URL}/api/v5/account/balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await okx.get_all_positions()

    assert result.exchange == "okx"
    assert len(result.positions) == 1
    assert result.positions[0].currency == "BTC"
    assert result.positions[0].available == 0.5


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance(respx_mock):
    """get_available_positions returns base currency balance."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)
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

    respx_mock.get(f"{OKX_BASE_URL}/api/v5/account/balance").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await okx.get_available_positions("BTC/USD")

    assert result.exchange == "okx"
    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.frozen == 0.1
    assert result.total == 0.6


# ---------------------------------------------------------------------------
# place_order error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_returns_error_on_okx_failure(respx_mock):
    """place_order returns (None, error_msg) when OKX rejects the order."""
    okx = OkxService(base_url=OKX_BASE_URL, simulated=True)
    okx_response = {
        "code": "1",
        "msg": "All operations failed",
        "data": [{
            "sCode": "51008",
            "sMsg": "Order failed. Your available SOL balance is insufficient.",
        }],
    }

    route = respx_mock.post(f"{OKX_BASE_URL}/api/v5/trade/order").mock(
        return_value=httpx.Response(200, json=okx_response),
    )

    order, err = await okx.place_order(
        PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1),
    )

    assert order is None
    assert err == "Order failed. Your available SOL balance is insufficient."

    # Verify the request itself looked correct.
    assert route.called
    req = route.calls.last.request
    assert req.method == "POST"
    body = req.content.decode()
    assert '"instId": "SOL-USDT"' in body
    assert '"side": "sell"' in body
    assert '"ordType": "market"' in body


# ---------------------------------------------------------------------------
# Order lifecycle (integration - requires API keys, hits paper-trading API)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_place_view_cancel_order(okx_svc: OkxService):
    """
    Full order lifecycle against OKX paper-trading: place a limit order
    far below market, verify it's pending, cancel it, verify it's gone.

    Skipped unless all OKX simulated-trading credentials are configured.
    """
    for var in ("OKX_API_KEY_SIMULATED", "OKX_API_SECRET_SIMULATED", "OKX_API_PASSPHRASE_SIMULATED"):
        if not os.getenv(var):
            pytest.skip(f"{var} not set; skipping live paper-trading test")

    order = PlaceOrderRequest(
        pair="BTC/USD",
        side="buy",
        type="limit",
        # Far below any realistic BTC price so the order cannot fill while
        # the test is running; we want a pure place -> list -> cancel cycle.
        price=1.00,
        size=0.0001,
    )
    placed, err = await okx_svc.place_order(order)
    assert err is None, f"place_order failed: {err}"
    assert placed is not None
    order_id = placed.id

    try:
        pending = await okx_svc.get_orders(pair="BTC/USD")
        found = [o for o in pending if o.id == order_id]
        assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

        cancelled = await okx_svc.cancel_order(order_id, "BTC/USD")
        assert cancelled is True, f"cancel_order returned False for order {order_id}"

        pending_after = await okx_svc.get_orders(pair="BTC/USD")
        still_there = [o for o in pending_after if o.id == order_id]
        assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
    finally:
        # Best-effort cleanup so a failed assertion doesn't leak an open
        # order on the paper account between runs.
        try:
            await okx_svc.cancel_order(order_id, "BTC/USD")
        except Exception:
            pass
