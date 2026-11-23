"""Unit tests for routes/bots.py, through a fake ProxySession.

What this module owns, and so what is tested here: the exact `/v1/bots`
payload for each route — above all the two things that differ from xlrts
(`backup: false` on every save, `placement: "window"` on start and launch) —
the files Launch Market generates, input validation before anything reaches
the gateway, and the ProxyError -> HTTP mapping.
"""

import json
import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_client.errors import (
    ActionNotPermittedError,
    AuthFailedError,
    MalformedRequestError,
    ProxyError,
)

from auth import current_container
from bot_templates import LaunchRequest, config_yaml, subaccount_json
from routes.bots import router

SHA = "a" * 64


class FakeProxy:
    def __init__(self):
        self.calls = []
        self.response = {}
        self.error = None

    async def call(self, exchange, action, payload=None, *, idempotency_key=""):
        self.calls.append((exchange, action, payload))
        if self.error is not None:
            raise self.error
        return self.response


class FakeContainer:
    def __init__(self, proxy):
        self.proxy = proxy


@pytest.fixture
def proxy():
    return FakeProxy()


@pytest.fixture
def client(proxy):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_container] = lambda: FakeContainer(proxy)
    return TestClient(app)


def launch_body(**over):
    body = {
        "market": "USDT_USD",
        "okx": {"enabled": True, "trading_pair": "USDT-USD", "reference_pair": "",
                "minimum_spread": "2.00", "center_buffer": "0.00", "tick_level": "0.0001"},
        "kraken": {"enabled": False, "trading_pair": "", "reference_pair": "",
                   "minimum_spread": "99.00", "center_buffer": "0.00", "tick_level": "0.0001",
                   "proxy_exchange": "kraken_prime"},
        "gemini": {"enabled": False, "trading_pair": "", "reference_pair": "",
                   "minimum_spread": "40.00", "center_buffer": "1.00", "tick_level": "0.0001"},
    }
    body.update(over)
    return body


# -- payloads ---------------------------------------------------------------


def test_list_is_list_markets(client, proxy):
    proxy.response = {"root": "/home/admin/speedbyte", "markets": []}
    r = client.get("/bots")
    assert r.status_code == 200 and r.json()["root"] == "/home/admin/speedbyte"
    assert proxy.calls == [("bots", "list_markets", {})]


def test_start_asks_for_a_cuquants_window(client, proxy):
    client.post("/bots/EURC_USD/start")
    assert proxy.calls == [("bots", "start", {"market": "EURC_USD", "placement": "window"})]


def test_stop(client, proxy):
    client.post("/bots/EURC_USD/stop")
    assert proxy.calls == [("bots", "stop", {"market": "EURC_USD"})]


def test_read_file(client, proxy):
    client.get("/bots/EURC_USD/files/subaccount")
    assert proxy.calls == [("bots", "read_file", {"market": "EURC_USD", "kind": "subaccount"})]


def test_save_never_asks_for_a_backup(client, proxy):
    r = client.post("/bots/EURC_USD/files/config", json={"content": "market: 'EURC_USD'\n", "base_sha256": SHA})
    assert r.status_code == 200
    assert proxy.calls == [("bots", "write_file", {
        "market": "EURC_USD", "kind": "config", "content": "market: 'EURC_USD'\n",
        "base_sha256": SHA, "backup": False,
    })]


def test_launch_sends_generated_files_and_window_placement(client, proxy):
    r = client.post("/bots/launch", json=launch_body())
    assert r.status_code == 200
    ((exchange, action, payload),) = proxy.calls
    assert (exchange, action) == ("bots", "launch_market")
    assert payload["market"] == "USDT_USD"
    assert payload["placement"] == "window"
    assert payload["config"].startswith("market: 'USDT_USD'\nsubaccount: 'USDT_USD'\n")
    assert json.loads(payload["subaccount"])["market"] == "USDT_USD"


# -- validation before the gateway ------------------------------------------


@pytest.mark.parametrize("path", [
    "/bots/sample/start", "/bots/-rf/start", "/bots/a%20b/stop", "/bots/.x/files/config",
])
def test_bad_market_names_never_reach_the_gateway(client, proxy, path):
    r = client.post(path) if not path.endswith("config") else client.get(path)
    assert r.status_code == 400
    assert proxy.calls == []


def test_unknown_file_kind_is_refused(client, proxy):
    assert client.get("/bots/EURC_USD/files/secrets").status_code == 422
    assert proxy.calls == []


def test_save_needs_the_base_hash(client, proxy):
    r = client.post("/bots/EURC_USD/files/config", json={"content": "x: 1\n", "base_sha256": ""})
    assert r.status_code == 422
    assert proxy.calls == []


@pytest.mark.parametrize("over", [
    {"market": "BAD NAME"},
    {"market": "sample'"},
    {"okx": {**launch_body()["okx"], "trading_pair": "X'\nmarket: 'EVIL"}},
    {"okx": {**launch_body()["okx"], "tick_level": "0"}},
    {"okx": {**launch_body()["okx"], "minimum_spread": "abc"}},
    {"okx": {**launch_body()["okx"], "minimum_spread": "NaN"}},
    {"kraken": {**launch_body()["kraken"], "proxy_exchange": "binance"}},
])
def test_launch_input_is_validated(client, proxy, over):
    assert client.post("/bots/launch", json=launch_body(**over)).status_code == 422
    assert proxy.calls == []


# -- the generated files ----------------------------------------------------


def test_config_writes_numbers_as_typed():
    cfg = config_yaml(LaunchRequest(**launch_body(
        okx={**launch_body()["okx"], "tick_level": "0.00001", "minimum_spread": "2.00"},
    )))
    assert "  tick_level: 0.00001\n" in cfg  # never 1e-05
    assert "  minimum_spread: 2.00 ## in bps\n" in cfg
    assert "  trading_pair: 'USDT-USD'\n  enabled: true\n" in cfg
    assert "  proxy_exchange: 'kraken_prime'\n" in cfg


def test_subaccount_splits_the_market_into_base_and_quote():
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    data = json.loads(subaccount_json("USDT_USD", now))
    assert data["balances"] == {
        v: {"USDT": 0.0, "USD": 0.0} for v in ("okx", "kraken", "gemini")
    }
    assert data["created_at"] == data["last_updated"] == now.isoformat()


# -- errors -----------------------------------------------------------------


@pytest.mark.parametrize(("error", "status"), [
    (ActionNotPermittedError("no", detail={"reason": "bot_role 'viewer' may not start (needs operator)"}), 403),
    (MalformedRequestError("bad", detail={"reason": "invalid market name"}), 400),
    (ProxyError("box said no", detail={"reason": "EURC_USD is already running (CUQuants:4)"}, code="BOT_ERROR"), 409),
    (ProxyError("odd", code="SOMETHING_NEW"), 502),
])
def test_gateway_refusals_keep_their_reason(client, proxy, error, status):
    proxy.error = error
    r = client.post("/bots/EURC_USD/start")
    assert r.status_code == status
    if isinstance(error.detail, dict):
        assert r.json()["detail"] == error.detail["reason"]


def test_a_dead_credential_is_left_to_the_app_handler(client, proxy):
    proxy.error = AuthFailedError("revoked")
    with pytest.raises(AuthFailedError):
        client.post("/bots/EURC_USD/start")
