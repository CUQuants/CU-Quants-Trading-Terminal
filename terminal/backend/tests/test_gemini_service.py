"""Gemini service unit tests.

These tests mock at the HTTP layer with ``respx`` (intercepts ``httpx``
calls) rather than patching the service's private ``_request`` method.
This lets us assert on the actual URL, method, auth headers
(``X-GEMINI-APIKEY``, ``X-GEMINI-SIGNATURE``), and the base64-encoded
JSON payload that Gemini receives.

Note: ``GeminiService(simulated=True)`` rewrites ``base_url`` inside
the constructor to point at the sandbox, so all respx mocks below
target the sandbox host even though tests pass production URLs.
"""

import base64
import json
import os

import httpx
import pytest

from exchange_services.gemini_service import GeminiService
from models import PlaceOrderRequest, TradeResponse


# GeminiService(simulated=True) forces base_url to the sandbox regardless
# of what's passed to the constructor; mocks must target the sandbox.
GEMINI_BASE_URL = "https://api.sandbox.gemini.com"


def _decode_gemini_payload(request: httpx.Request) -> dict:
    """Extract and decode the X-GEMINI-PAYLOAD header on a request."""
    return json.loads(base64.b64decode(request.headers["X-GEMINI-PAYLOAD"]))


# Sample Gemini mytrades response (matches /v1/mytrades format).
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


# ---------------------------------------------------------------------------
# get_trades (mytrades)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_parses_mytrades_correctly(respx_mock):
    """GeminiService.get_trades parses mytrades into TradeResponse list."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    respx_mock.post(f"{GEMINI_BASE_URL}/v1/mytrades").mock(
        return_value=httpx.Response(200, json=GEMINI_TRADES_RESPONSE),
    )

    trades = await gemini.get_trades(limit=10)

    assert isinstance(trades, list)
    assert len(trades) == 2

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

    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.role == "taker"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit(respx_mock):
    """get_trades with pair filter sends symbol + limit_trades in payload."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    route = respx_mock.post(f"{GEMINI_BASE_URL}/v1/mytrades").mock(
        return_value=httpx.Response(200, json=GEMINI_TRADES_RESPONSE[:1]),
    )

    await gemini.get_trades(pair="ETH/USD", limit=5)

    assert route.called
    payload = _decode_gemini_payload(route.calls.last.request)
    assert payload["symbol"] == "ethusd"
    assert payload["limit_trades"] == 5
    # Auth headers must be present.
    req = route.calls.last.request
    assert req.headers.get("X-GEMINI-APIKEY") is not None
    assert req.headers.get("X-GEMINI-SIGNATURE")


@pytest.mark.asyncio
async def test_get_trades_empty_response(respx_mock):
    """get_trades handles empty array without error."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    respx_mock.post(f"{GEMINI_BASE_URL}/v1/mytrades").mock(
        return_value=httpx.Response(200, json=[]),
    )

    trades = await gemini.get_trades()
    assert trades == []


# ---------------------------------------------------------------------------
# Account balance endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance(respx_mock):
    """get_available_cash returns quote currency (USD) balance."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "USD", "amount": "1234.56", "available": "1234.56"},
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
    ]

    respx_mock.post(f"{GEMINI_BASE_URL}/v1/balances").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await gemini.get_available_cash("BTC/USD")

    assert result.exchange == "gemini"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen >= 0
    assert result.total == 1234.56


@pytest.mark.asyncio
async def test_get_all_balances_returns_all_currencies(respx_mock):
    """get_all_balances returns all currencies from full balance response."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "USD", "amount": "1000", "available": "1000"},
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
    ]

    respx_mock.post(f"{GEMINI_BASE_URL}/v1/balances").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await gemini.get_all_balances()

    assert result.exchange == "gemini"
    assert len(result.currencies) == 2
    usd = next(c for c in result.currencies if c.currency == "USD")
    assert usd.available == 1000
    btc = next(c for c in result.currencies if c.currency == "BTC")
    assert btc.available == 0.5


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero(respx_mock):
    """get_all_positions returns only non-zero, non-stablecoin holdings."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "USD", "amount": "1000", "available": "1000"},
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
        {"currency": "ETH", "amount": "0", "available": "0"},
    ]

    respx_mock.post(f"{GEMINI_BASE_URL}/v1/balances").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await gemini.get_all_positions()

    assert result.exchange == "gemini"
    assert len(result.positions) == 1
    assert result.positions[0].currency == "BTC"
    assert result.positions[0].available == 0.5


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance(respx_mock):
    """get_available_positions returns base currency balance."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    balance_response = [
        {"currency": "BTC", "amount": "0.5", "available": "0.5"},
        {"currency": "USD", "amount": "1000", "available": "1000"},
    ]

    respx_mock.post(f"{GEMINI_BASE_URL}/v1/balances").mock(
        return_value=httpx.Response(200, json=balance_response),
    )

    result = await gemini.get_available_positions("BTC/USD")

    assert result.exchange == "gemini"
    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.total >= 0.5


# ---------------------------------------------------------------------------
# place_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_returns_error_on_gemini_failure(respx_mock):
    """place_order returns (None, error_msg) when Gemini rejects the order."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    gemini_response = {
        "result": "error",
        "reason": "InsufficientBalance",
        "message": "Insufficient balance for order",
    }

    # Market orders normalize the price via the symbols/details endpoint.
    respx_mock.get(f"{GEMINI_BASE_URL}/v1/symbols/details/solusd").mock(
        return_value=httpx.Response(200, json={"quote_increment": "0.01"}),
    )
    respx_mock.post(f"{GEMINI_BASE_URL}/v1/order/new").mock(
        return_value=httpx.Response(200, json=gemini_response),
    )

    order, err = await gemini.place_order(
        PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1, price=100.0),
    )

    assert order is None
    assert err is not None
    assert "Insufficient" in err or "balance" in err.lower()


@pytest.mark.asyncio
async def test_place_order_market_requires_explicit_price(respx_mock):
    """Market orders should be rejected when no explicit price is provided.

    No HTTP call should be made at all — respx's default strict mode
    fails the test if any unmocked request is attempted, which doubles
    as an assertion that the service short-circuits before networking.
    """
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    order, err = await gemini.place_order(
        PlaceOrderRequest(pair="SOL/USD", side="buy", type="market", size=1),
    )

    assert order is None
    assert err == "Market orders require price"
    # No routes registered → no requests should have been made.
    assert len(respx_mock.calls) == 0


@pytest.mark.asyncio
async def test_place_order_market_uses_explicit_price_without_ticker_lookup(respx_mock):
    """Market order should use provided price directly and keep IOC behavior.

    The ticker endpoint is intentionally NOT mocked — if the service
    code attempts to call it, respx will raise (strict mode) and the
    test will fail with a clear "unmocked request" error.
    """
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    respx_mock.get(f"{GEMINI_BASE_URL}/v1/symbols/details/solusd").mock(
        return_value=httpx.Response(200, json={"quote_increment": "0.01"}),
    )
    order_route = respx_mock.post(f"{GEMINI_BASE_URL}/v1/order/new").mock(
        return_value=httpx.Response(200, json={"order_id": "1", "is_live": True, "timestamp": "1730385593"}),
    )

    order, err = await gemini.place_order(
        PlaceOrderRequest(pair="SOL/USD", side="buy", type="market", size=1, price=123.4567),
    )

    assert err is None
    assert order is not None
    assert order_route.called
    payload = _decode_gemini_payload(order_route.calls.last.request)
    assert payload["options"] == ["immediate-or-cancel"]
    assert payload["price"] == "123.46"


@pytest.mark.asyncio
async def test_place_order_market_uses_symbol_increment_rounding(respx_mock):
    """Market IOC prices should use provided references and valid quote increment rounding."""
    service = GeminiService(base_url="https://api.gemini.com", simulated=True)

    # symbols/details is hit once and the increment is cached for the
    # second place_order call.
    respx_mock.get(f"{GEMINI_BASE_URL}/v1/symbols/details/ethusd").mock(
        return_value=httpx.Response(200, json={"quote_increment": "0.01"}),
    )
    order_route = respx_mock.post(f"{GEMINI_BASE_URL}/v1/order/new").mock(
        side_effect=[
            httpx.Response(200, json={"order_id": "1", "is_live": True, "timestamp": "1730385593"}),
            httpx.Response(200, json={"order_id": "2", "is_live": True, "timestamp": "1730385593"}),
        ],
    )

    _, buy_err = await service.place_order(
        PlaceOrderRequest(pair="ETH/USD", side="buy", type="market", size=0.01, price=3047.50),
    )
    _, sell_err = await service.place_order(
        PlaceOrderRequest(pair="ETH/USD", side="sell", type="market", size=0.01, price=3047.00),
    )

    assert buy_err is None
    assert sell_err is None
    assert order_route.call_count == 2

    buy_payload = _decode_gemini_payload(order_route.calls[0].request)
    sell_payload = _decode_gemini_payload(order_route.calls[1].request)
    assert buy_payload["price"] == "3047.5"
    assert sell_payload["price"] == "3047"


@pytest.mark.asyncio
async def test_place_order_limit_price_is_rounded_to_increment(respx_mock):
    """Limit order prices should be normalized to valid quote increment."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)

    respx_mock.get(f"{GEMINI_BASE_URL}/v1/symbols/details/ethusd").mock(
        return_value=httpx.Response(200, json={"quote_increment": "0.01"}),
    )
    order_route = respx_mock.post(f"{GEMINI_BASE_URL}/v1/order/new").mock(
        return_value=httpx.Response(200, json={"order_id": "1", "is_live": True, "timestamp": "1730385593"}),
    )

    order, err = await gemini.place_order(
        PlaceOrderRequest(pair="ETH/USD", side="buy", type="limit", size=0.01, price=3047.57555),
    )

    assert err is None
    assert order is not None
    payload = _decode_gemini_payload(order_route.calls.last.request)
    assert payload["price"] == "3047.58"


@pytest.mark.asyncio
async def test_gemini_request_omits_account_when_not_configured(respx_mock):
    """``account`` should only be sent in the payload when explicitly configured."""
    gemini = GeminiService(base_url="https://api.gemini.com", simulated=True)
    gemini.api_key = "non-master-key"
    gemini.is_master_api_key = False
    gemini.account = ""

    route = respx_mock.post(f"{GEMINI_BASE_URL}/v1/mytrades").mock(
        return_value=httpx.Response(200, json=[]),
    )

    await gemini.get_trades(pair="ETH/USD", limit=1)

    assert route.called
    payload = _decode_gemini_payload(route.calls.last.request)
    assert "account" not in payload


# ---------------------------------------------------------------------------
# Order lifecycle (integration - hits real Gemini API)
# ---------------------------------------------------------------------------
# WARNING: this test defaults to production Gemini. Switch the gemini_svc
# fixture's base_url to https://api.sandbox.gemini.com if you'd rather
# run against the paper-trading sandbox.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_place_view_cancel_order(gemini_svc: GeminiService):
    """Full order lifecycle: place limit away from market, list, cancel, verify gone."""
    for var in ("GEMINI_API_KEY", "GEMINI_API_SECRET"):
        if not os.getenv(var):
            pytest.skip(f"{var} not set; skipping live Gemini lifecycle test")

    pair = "BTC/USD"
    symbol = "btcusd"

    try:
        async with httpx.AsyncClient() as client:
            ticker_resp = await client.get(f"{gemini_svc.base_url}/v2/ticker/{symbol}")
            ticker_resp.raise_for_status()
            ticker = ticker_resp.json()
    except Exception:
        pytest.skip("Gemini ticker unavailable for integration lifecycle test")

    bid = float(ticker.get("bid") or ticker.get("last") or 0)
    ask = float(ticker.get("ask") or ticker.get("last") or 0)
    if bid <= 0 or ask <= 0:
        pytest.skip("Gemini ticker unavailable for integration lifecycle test")

    cash = await gemini_svc.get_available_cash(pair)
    pos = await gemini_svc.get_available_positions(pair)
    min_notional_usd = 10.0

    order: PlaceOrderRequest
    if cash.available >= min_notional_usd:
        buy_price = max(bid * 0.95, 0.01)
        buy_size = max(0.00001, min(0.001, (cash.available * 0.5) / buy_price))
        if buy_size * buy_price >= min_notional_usd:
            order = PlaceOrderRequest(
                pair=pair,
                side="buy",
                type="limit",
                price=buy_price,
                size=buy_size,
            )
        else:
            pytest.skip("Insufficient USD notional for buy lifecycle test")
    elif pos.available > 0 and (pos.available * ask) >= min_notional_usd:
        sell_price = ask * 1.05
        sell_size = max(0.00001, min(0.001, pos.available * 0.5))
        if sell_size * sell_price < min_notional_usd:
            pytest.skip("Insufficient BTC notional for sell lifecycle test")
        order = PlaceOrderRequest(
            pair=pair,
            side="sell",
            type="limit",
            price=sell_price,
            size=sell_size,
        )
    else:
        pytest.skip("Insufficient balances for integration lifecycle test")

    placed, err = await gemini_svc.place_order(order)
    if err is not None:
        if "GenericFailure" in err or "insufficient" in err.lower() or "balance" in err.lower():
            pytest.skip(f"Exchange rejected integration lifecycle order: {err}")
        pytest.fail(f"place_order failed: {err}")
    assert placed is not None
    order_id = placed.id

    try:
        pending = await gemini_svc.get_orders(pair=pair)
        found = [o for o in pending if o.id == order_id]
        assert len(found) == 1, f"Order {order_id} not found in pending: {pending}"

        cancelled = await gemini_svc.cancel_order(order_id, pair)
        assert cancelled is True, f"cancel_order returned False for order {order_id}"

        pending_after = await gemini_svc.get_orders(pair=pair)
        still_there = [o for o in pending_after if o.id == order_id]
        assert len(still_there) == 0, f"Order {order_id} still pending after cancel"
    finally:
        # Best-effort cleanup so a failed assertion doesn't leak an open
        # order between runs.
        try:
            await gemini_svc.cancel_order(order_id, pair)
        except Exception:
            pass
