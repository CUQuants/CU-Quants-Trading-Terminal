"""Unit tests for KrakenService, driven through a fake ProxySession.

KrakenService no longer signs its own requests. It calls
`ProxySession.call("kraken_prime", <action>, <payload>)`, and the gateway
returns Kraken's own body unreshaped (`{"error": [], "result": {...}}`).
These tests stub that one method and check the payloads sent and the
parsing of what comes back.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_client.errors import ActionNotPermittedError, ExchangeError

from exchange_services.kraken_service import EXCHANGE, KrakenService
from models import PlaceOrderRequest, TradeResponse


class FakeProxy:
    """Stands in for ProxySession. Records calls; returns canned bodies (or
    raises a canned exception) keyed by action."""

    def __init__(self):
        self.calls = []
        self._responses = {}

    def set(self, action, response):
        self._responses[action] = response

    async def call(self, exchange, action, payload=None, *, idempotency_key=""):
        self.calls.append({"exchange": exchange, "action": action, "payload": payload,
                           "idempotency_key": idempotency_key})
        r = self._responses.get(action)
        if isinstance(r, Exception):
            raise r
        return r if r is not None else {"error": [], "result": {}}

    @property
    def last(self):
        return self.calls[-1]


@pytest.fixture
def proxy():
    return FakeProxy()


@pytest.fixture
def kraken(proxy):
    return KrakenService(proxy)


def kraken_rejection(*errors, outcome_unknown=False):
    """What the gateway raises (via the SDK) when Kraken answers with an error."""
    return ExchangeError(
        "kraken declined the request",
        detail={"kraken_error": list(errors), "body": {"error": list(errors), "result": {}},
                "exchange": EXCHANGE, "outcome_unknown": outcome_unknown},
    )


# ---------------------------------------------------------------------------
# Every call goes to the Prime account through the gateway
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_call_targets_kraken_prime(kraken, proxy):
    proxy.set("place_order", {"error": [], "result": {"txid": ["OABC"]}})
    await kraken.place_order(PlaceOrderRequest(pair="BTC/USD", side="buy", type="limit", price=1000, size=1))
    await kraken.get_orders(pair="BTC/USD")
    await kraken.cancel_order("OABC", "BTC/USD")
    await kraken.get_all_balances()

    assert [c["exchange"] for c in proxy.calls] == ["kraken_prime"] * 4
    assert [c["action"] for c in proxy.calls] == [
        "place_order", "get_pending_orders", "cancel_order", "get_balance"]


@pytest.mark.asyncio
async def test_only_mutating_calls_carry_an_idempotency_key(kraken, proxy):
    proxy.set("place_order", {"error": [], "result": {"txid": ["OABC"]}})
    await kraken.place_order(PlaceOrderRequest(pair="BTC/USD", side="buy", type="limit", price=1000, size=1))
    await kraken.cancel_order("OABC", "BTC/USD")
    await kraken.get_orders(pair="BTC/USD")
    await kraken.get_all_balances()

    keys = [c["idempotency_key"] for c in proxy.calls]
    assert keys[0] and keys[1] and keys[0] != keys[1]
    assert keys[2] == keys[3] == ""


# ---------------------------------------------------------------------------
# place_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_limit_order_payload_and_result(kraken, proxy):
    proxy.set("place_order", {"error": [], "result": {
        "txid": ["OQCLML-BW3P3-BUCMWZ"], "descr": {"order": "buy 1.00000000 XBTUSD @ limit 1000.0"}}})

    order, err = await kraken.place_order(
        PlaceOrderRequest(pair="BTC/USD", side="buy", type="limit", price=1000.0, size=1))

    assert err is None
    assert proxy.last["payload"] == {
        "pair": "XBTUSD", "type": "buy", "ordertype": "limit", "volume": "1.0", "price": "1000.0"}
    assert order.id == "OQCLML-BW3P3-BUCMWZ"
    assert order.exchange == "kraken"
    assert order.pair == "BTC/USD"
    assert order.status == "live"


@pytest.mark.asyncio
async def test_iceberg_order_sends_displayvol(kraken, proxy):
    proxy.set("place_order", {"error": [], "result": {"txid": ["OICE"]}})
    _, err = await kraken.place_order(PlaceOrderRequest(
        pair="BTC/USD", side="buy", type="iceberg", price=1000.0, size=1.5, visible_size=0.5))

    assert err is None
    assert proxy.last["payload"]["displayvol"] == "0.5"


@pytest.mark.asyncio
async def test_iceberg_validation_happens_before_any_call(kraken, proxy):
    _, err = await kraken.place_order(PlaceOrderRequest(
        pair="BTC/USD", side="buy", type="iceberg", price=1000.0, size=1.0))

    assert err == "visible_size is required for iceberg orders"
    assert proxy.calls == []


@pytest.mark.asyncio
async def test_place_order_returns_krakens_error(kraken, proxy):
    proxy.set("place_order", kraken_rejection("EOrder:Insufficient funds"))

    order, err = await kraken.place_order(PlaceOrderRequest(pair="SOL/USD", side="sell", type="market", size=1))

    assert order is None
    assert err == "EOrder:Insufficient funds"


@pytest.mark.asyncio
async def test_place_order_outcome_unknown_says_so(kraken, proxy):
    """A timeout after forwarding: the order may exist. Saying so stops a
    trader from blindly placing it again."""
    proxy.set("place_order", kraken_rejection("timeout", outcome_unknown=True))

    order, err = await kraken.place_order(PlaceOrderRequest(pair="BTC/USD", side="buy", type="market", size=1))

    assert order is None
    assert "outcome unknown" in err.lower()


@pytest.mark.asyncio
async def test_place_order_returns_gateway_refusals(kraken, proxy):
    proxy.set("place_order", ActionNotPermittedError("kraken_prime registers no route"))

    order, err = await kraken.place_order(PlaceOrderRequest(pair="BTC/USD", side="buy", type="market", size=1))

    assert order is None
    assert "no route" in err


# ---------------------------------------------------------------------------
# get_orders / cancel_order
# ---------------------------------------------------------------------------

OPEN_ORDERS = {"error": [], "result": {"open": {
    "OBTC-1": {"cl_ord_id": "c1", "status": "open", "opentm": 1793819215.22, "vol": "0.00006000",
               "descr": {"pair": "XBTUSD", "type": "buy", "ordertype": "limit", "price": "40102.2"}},
    "OSOL-1": {"status": "open", "opentm": 1793819216.0, "vol": "2.0", "display_volume": "0.5",
               "descr": {"pair": "SOLUSD", "type": "sell", "ordertype": "iceberg", "price": "250.0"}},
}}}


@pytest.mark.asyncio
async def test_get_orders_parses_and_filters_by_pair(kraken, proxy):
    proxy.set("get_pending_orders", OPEN_ORDERS)

    orders = await kraken.get_orders(pair="BTC/USD")

    assert proxy.last["payload"] == {}
    assert [o.id for o in orders] == ["OBTC-1"]
    o = orders[0]
    assert (o.pair, o.side, o.type, o.price, o.size, o.status) == (
        "BTC/USD", "buy", "limit", 40102.2, 0.00006, "open")


@pytest.mark.asyncio
async def test_get_orders_without_pair_returns_everything(kraken, proxy):
    proxy.set("get_pending_orders", OPEN_ORDERS)

    orders = {o.id: o for o in await kraken.get_orders()}

    assert set(orders) == {"OBTC-1", "OSOL-1"}
    assert orders["OSOL-1"].type == "iceberg"
    assert orders["OSOL-1"].visible_size == 0.5


@pytest.mark.asyncio
async def test_cancel_order_sends_the_txid(kraken, proxy):
    proxy.set("cancel_order", {"error": [], "result": {"count": 1}})

    assert await kraken.cancel_order("OBTC-1", "BTC/USD") is True
    assert proxy.last["payload"] == {"txid": "OBTC-1"}


@pytest.mark.asyncio
async def test_cancel_order_that_cancelled_nothing_is_a_failure(kraken, proxy):
    proxy.set("cancel_order", {"error": [], "result": {"count": 0}})
    assert await kraken.cancel_order("OBTC-1", "BTC/USD") is False


@pytest.mark.asyncio
async def test_cancel_order_rejected_is_a_failure(kraken, proxy):
    proxy.set("cancel_order", kraken_rejection("EOrder:Unknown order"))
    assert await kraken.cancel_order("ONOPE", "BTC/USD") is False


@pytest.mark.asyncio
async def test_place_view_cancel_order(kraken, proxy):
    """The lifecycle the terminal drives: place, see it open, cancel, see it gone."""
    proxy.set("place_order", {"error": [], "result": {"txid": ["OLIFE-1"]}})
    placed, err = await kraken.place_order(
        PlaceOrderRequest(pair="BTC/USD", side="buy", type="limit", price=1000.0, size=0.0001))
    assert err is None

    proxy.set("get_pending_orders", {"error": [], "result": {"open": {"OLIFE-1": {
        "status": "open", "vol": "0.0001",
        "descr": {"pair": "XBTUSD", "type": "buy", "ordertype": "limit", "price": "1000.0"}}}}})
    assert [o.id for o in await kraken.get_orders(pair="BTC/USD")] == [placed.id]

    proxy.set("cancel_order", {"error": [], "result": {"count": 1}})
    assert await kraken.cancel_order(placed.id, "BTC/USD") is True

    proxy.set("get_pending_orders", {"error": [], "result": {"open": {}}})
    assert await kraken.get_orders(pair="BTC/USD") == []


# ---------------------------------------------------------------------------
# Balances (Kraken BalanceEx shape)
# ---------------------------------------------------------------------------

BALANCE_EX = {"error": [], "result": {
    "ZUSD": {"balance": "1234.5600", "hold_trade": "34.5600"},
    "XXBT": {"balance": "0.5000000000", "hold_trade": "0.0000000000"},
    "XETH": {"balance": "0.0000000000", "hold_trade": "0.0000000000"},
    "SOL": {"balance": "3.0", "hold_trade": "1.0"},
}}


@pytest.mark.asyncio
async def test_get_available_cash_subtracts_held_funds(kraken, proxy):
    proxy.set("get_balance", BALANCE_EX)

    result = await kraken.get_available_cash("BTC/USD")

    assert result.exchange == "kraken"
    assert result.currency == "USD"
    assert result.total == pytest.approx(1234.56)
    assert result.frozen == pytest.approx(34.56)
    assert result.available == pytest.approx(1200.0)


@pytest.mark.asyncio
async def test_get_available_positions_finds_legacy_asset_codes(kraken, proxy):
    """XXBT has to be found for BTC (the lookup used to try only XBT)."""
    proxy.set("get_balance", BALANCE_EX)

    result = await kraken.get_available_positions("BTC/USD")

    assert result.base_currency == "BTC"
    assert result.available == 0.5
    assert result.total == 0.5


@pytest.mark.asyncio
async def test_get_all_balances_normalizes_every_currency(kraken, proxy):
    proxy.set("get_balance", BALANCE_EX)

    result = await kraken.get_all_balances()

    by_ccy = {c.currency: c for c in result.currencies}
    assert set(by_ccy) == {"USD", "BTC", "ETH", "SOL"}
    assert by_ccy["SOL"].available == 2.0
    assert by_ccy["SOL"].frozen == 1.0


@pytest.mark.asyncio
async def test_get_all_positions_excludes_cash_and_zero(kraken, proxy):
    proxy.set("get_balance", BALANCE_EX)

    result = await kraken.get_all_positions()

    assert {p.currency for p in result.positions} == {"BTC", "SOL"}


@pytest.mark.asyncio
async def test_a_currency_under_two_codes_is_added_together(kraken, proxy):
    proxy.set("get_balance", {"error": [], "result": {
        "XXBT": {"balance": "0.5", "hold_trade": "0"}, "XBT": {"balance": "0.25", "hold_trade": "0"}}})

    result = await kraken.get_available_positions("BTC/USD")

    assert result.total == 0.75


@pytest.mark.asyncio
async def test_missing_currency_is_zero(kraken, proxy):
    proxy.set("get_balance", BALANCE_EX)
    result = await kraken.get_available_cash("BTC/EUR")
    assert (result.available, result.frozen, result.total) == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Trades: not routed for Prime yet
# ---------------------------------------------------------------------------

KRAKEN_TRADES_RESPONSE = {"error": [], "result": {"count": 2, "trades": {
    "TXNID-SOL-001": {"ordertxid": "ORD-SOL-001", "pair": "SOLUSD", "time": 1730385593.0, "type": "buy",
                      "price": "82.01", "cost": "82.01", "fee": "0.002", "vol": "1.0", "misc": ""},
    "TXNID-BTC-001": {"ordertxid": "ORD-BTC-001", "pair": "XXBTZUSD", "time": 1730385600.0, "type": "sell",
                      "price": "95000.50", "cost": "95.0005", "fee": "0.095", "vol": "0.001", "misc": ""},
}}}


@pytest.mark.asyncio
async def test_get_trades_is_empty_while_the_gateway_does_not_route_fills(kraken, proxy):
    proxy.set("get_fills", ActionNotPermittedError("kraken_prime registers no route for action 'get_fills'"))
    assert await kraken.get_trades() == []


@pytest.mark.asyncio
async def test_get_trades_parses_fills_once_they_are_routed(kraken, proxy):
    proxy.set("get_fills", KRAKEN_TRADES_RESPONSE)

    trades = await kraken.get_trades(pair="BTC/USD", limit=5)

    assert proxy.last["payload"] == {"pair": "XBTUSD"}
    by_id = {t.id: t for t in trades}
    assert isinstance(by_id["TXNID-BTC-001"], TradeResponse)
    assert by_id["TXNID-BTC-001"].pair == "BTC/USD"
    assert by_id["TXNID-BTC-001"].side == "sell"
    assert by_id["TXNID-SOL-001"].fee == 0.002


# ---------------------------------------------------------------------------
# Order stream: none for Prime
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_order_stream_is_a_no_op(kraken, proxy):
    import asyncio

    queue: asyncio.Queue = asyncio.Queue()
    await kraken.start_order_stream(queue)
    await kraken.stop_order_stream()

    assert queue.empty()
    assert proxy.calls == []
