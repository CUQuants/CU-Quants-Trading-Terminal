"""Unit tests for OkxService — driven through a fake ProxySession.

OkxService no longer signs its own requests; it calls
`ProxySession.call("okx", <action>, <payload>)` and the Proxy returns OKX's
own body unreshaped. These tests stub that one method and assert the
service still builds the right payloads and parses the responses the same
way it always did.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_client.errors import ExchangeError

from exchange_services.okx_service import OkxService
from models import PlaceOrderRequest, TradeResponse


class FakeProxy:
    """Stands in for ProxySession. Records calls, returns canned bodies (or
    raises a canned exception) keyed by action."""

    def __init__(self):
        self.calls = []
        self._responses = {}

    def set(self, action, response):
        self._responses[action] = response

    async def call(self, exchange, action, payload=None, *, idempotency_key=""):
        self.calls.append(
            {"exchange": exchange, "action": action, "payload": payload,
             "idempotency_key": idempotency_key}
        )
        r = self._responses.get(action)
        if isinstance(r, Exception):
            raise r
        return r if r is not None else {"code": "0", "data": []}

    @property
    def last(self):
        return self.calls[-1]


@pytest.fixture
def proxy():
    return FakeProxy()


@pytest.fixture
def okx(proxy):
    return OkxService(proxy)


OKX_FILLS_RESPONSE = {
    "code": "0",
    "msg": "",
    "data": [
        {
            "instType": "SPOT", "instId": "SOL-USDT", "tradeId": "123456789",
            "ordId": "987654321", "fillPx": "82.01", "fillSz": "1.0", "side": "buy",
            "execType": "M", "fee": "-0.002", "feeCcy": "SOL",
            "fillTime": "1730385593000", "ts": "1730385593000",
        },
        {
            "instType": "SPOT", "instId": "BTC-USDT", "tradeId": "111222333",
            "ordId": "444555666", "fillPx": "95000.50", "fillSz": "0.001", "side": "sell",
            "execType": "T", "fee": "0.095", "feeCcy": "USDT",
            "fillTime": "1730385600000", "ts": "1730385600000",
        },
    ],
}


# ---------------------------------------------------------------------------
# get_trades
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_parses_fills_correctly(okx, proxy):
    proxy.set("get_fills", OKX_FILLS_RESPONSE)
    trades = await okx.get_trades(limit=10)

    assert proxy.last["action"] == "get_fills"
    assert isinstance(trades, list) and len(trades) == 2

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

    t1 = trades[1]
    assert t1.pair == "BTC/USD"
    assert t1.side == "sell"
    assert t1.role == "taker"
    assert t1.fee == 0.095


@pytest.mark.asyncio
async def test_get_trades_pair_filter_and_limit_go_into_payload(okx, proxy):
    proxy.set("get_fills", {"code": "0", "data": OKX_FILLS_RESPONSE["data"][:1]})
    await okx.get_trades(pair="ETH/USD", limit=5)

    assert proxy.last["payload"] == {
        "instType": "SPOT", "limit": "5", "instId": "ETH-USDT",
    }


@pytest.mark.asyncio
async def test_get_trades_empty(okx, proxy):
    proxy.set("get_fills", {"code": "0", "data": []})
    assert await okx.get_trades() == []


# ---------------------------------------------------------------------------
# balances
# ---------------------------------------------------------------------------


def _balances(details):
    return {"code": "0", "data": [{"details": details}]}


@pytest.mark.asyncio
async def test_get_available_cash_parses_balance(okx, proxy):
    proxy.set("get_balance", _balances([
        {"ccy": "USDT", "availBal": "1234.56", "frozenBal": "100.00", "eq": "1334.56"},
    ]))
    result = await okx.get_available_cash("BTC/USD")

    assert proxy.last["action"] == "get_balance"
    assert result.exchange == "okx"
    assert result.currency == "USD"
    assert result.available == 1234.56
    assert result.frozen == 100.0
    assert result.total == 1334.56


@pytest.mark.asyncio
async def test_get_all_balances_returns_all_currencies(okx, proxy):
    proxy.set("get_balance", _balances([
        {"ccy": "USDT", "availBal": "1000", "frozenBal": "0", "eq": "1000"},
        {"ccy": "BTC", "availBal": "0.5", "frozenBal": "0.1", "eq": "0.6"},
    ]))
    result = await okx.get_all_balances()

    assert result.exchange == "okx"
    assert len(result.currencies) == 2
    usd = next(c for c in result.currencies if c.currency == "USD")
    assert usd.available == 1000
    btc = next(c for c in result.currencies if c.currency == "BTC")
    assert btc.available == 0.5 and btc.frozen == 0.1


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero(okx, proxy):
    proxy.set("get_balance", _balances([
        {"ccy": "USDT", "availBal": "1000", "frozenBal": "0", "eq": "1000"},
        {"ccy": "BTC", "availBal": "0.5", "frozenBal": "0", "eq": "0.5"},
        {"ccy": "ETH", "availBal": "0", "frozenBal": "0", "eq": "0"},
    ]))
    result = await okx.get_all_positions()

    assert len(result.positions) == 1
    assert result.positions[0].currency == "BTC"
    assert result.positions[0].available == 0.5


@pytest.mark.asyncio
async def test_get_available_positions_parses_balance(okx, proxy):
    proxy.set("get_balance", _balances([
        {"ccy": "BTC", "availBal": "0.5", "frozenBal": "0.1", "eq": "0.6"},
    ]))
    result = await okx.get_available_positions("BTC/USD")

    assert result.pair == "BTC/USD"
    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.frozen == 0.1
    assert result.total == 0.6


# ---------------------------------------------------------------------------
# place_order / cancel_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_builds_spot_payload_with_idempotency_key(okx, proxy):
    proxy.set("place_order", {"code": "0", "data": [{"ordId": "OKX-1"}]})
    order, err = await okx.place_order(
        PlaceOrderRequest(pair="BTC/USD", side="buy", type="limit", price=1000.0, size=1),
    )

    assert err is None
    assert order is not None and order.id == "OKX-1" and order.status == "live"

    call = proxy.last
    assert call["exchange"] == "okx" and call["action"] == "place_order"
    assert call["payload"] == {
        "instId": "BTC-USDT", "tdMode": "cash", "side": "buy",
        "ordType": "limit", "sz": "1.0", "px": "1000.0",
    }
    assert call["idempotency_key"]  # generated, non-empty


@pytest.mark.asyncio
async def test_place_order_maps_exchange_error_to_message(okx, proxy):
    proxy.set("place_order", ExchangeError(
        "code 1",
        detail={"okx_code": "1", "body": {
            "code": "1", "msg": "All operations failed",
            "data": [{"sCode": "51008",
                      "sMsg": "Order failed. Your available SOL balance is insufficient."}],
        }},
    ))
    order, err = await okx.place_order(
        PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1),
    )

    assert order is None
    assert err == "Order failed. Your available SOL balance is insufficient."


@pytest.mark.asyncio
async def test_cancel_order_true_on_success_false_on_error(okx, proxy):
    proxy.set("cancel_order", {"code": "0", "data": [{"ordId": "OKX-1"}]})
    assert await okx.cancel_order("OKX-1", "BTC/USD") is True
    assert proxy.last["idempotency_key"]

    proxy.set("cancel_order", ExchangeError("code 1", detail={"body": {"code": "1"}}))
    assert await okx.cancel_order("OKX-1", "BTC/USD") is False


# ---------------------------------------------------------------------------
# get_orders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_orders_parses_pending(okx, proxy):
    proxy.set("get_pending_orders", {"code": "0", "data": [
        {"ordId": "O1", "instId": "BTC-USDT", "side": "buy", "ordType": "limit",
         "px": "1000", "sz": "0.5", "state": "live", "cTime": "1730000000000"},
    ]})
    orders = await okx.get_orders(pair="BTC/USD")

    assert proxy.last["action"] == "get_pending_orders"
    assert proxy.last["payload"] == {"instType": "SPOT", "instId": "BTC-USDT"}
    assert len(orders) == 1
    assert orders[0].id == "O1"
    assert orders[0].pair == "BTC/USD"
    assert orders[0].price == 1000.0
    assert orders[0].size == 0.5
    assert orders[0].status == "live"
