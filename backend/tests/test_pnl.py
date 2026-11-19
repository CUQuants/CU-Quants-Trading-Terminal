"""PnL: `ProxySession.get_pnl` (the signed `POST /v1/rmu/pnl`) and the
terminal's `GET /pnl` route. The gateway is an `httpx.MockTransport`."""

import json
import os
import sys

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_client.errors import ProxyError
from proxy_client.signing import compute_signature

from exchange_services.proxy_session import ProxySession
from auth import current_container
from routes.pnl import router

SECRET = "c2VjcmV0LXNlY3JldA=="
REPORT = {
    "as_of": "2026-11-14T23:27:43+00:00",
    "group_by": "pair",
    "pair_pnl": {"running": True, "error": None, "untracked": []},
    "groups": [{"key": "kraken_prime:USDQ-USD", "position": "15.02025000", "pnl": "0.0225"}],
    "totals": {"USD": {"realized": "0", "unrealized": "0.0225", "fees": "0", "pnl": "0.0225", "complete": True}},
    "total": {"ccy": "USD", "pnl": "0.0225", "complete": True, "missing": []},
    "portfolio": {"quote_ccy": "USD", "nav": "500.80", "complete": True},
}


def _session(handler) -> ProxySession:
    s = ProxySession("http://gw.test", "cuq_op_key", SECRET, "cuq-001", "Sammy")
    s._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return s


@pytest.mark.asyncio
async def test_get_pnl_signs_the_pnl_path_and_returns_the_report_unchanged():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=REPORT)

    report = await _session(handler).get_pnl()

    assert report == REPORT
    req = seen[0]
    assert req.method == "POST" and req.url.path == "/v1/rmu/pnl"
    body = req.content
    assert json.loads(body) == {"operator_id": "cuq-001", "operator_name": "Sammy",
                                "payload": {"group_by": "pair"}}
    assert "system_name" not in json.loads(body)  # operator credential
    expected = compute_signature(SECRET.encode(), "POST", "/v1/rmu/pnl",
                                 req.headers["X-Timestamp"], req.headers["X-Nonce"], body)
    assert req.headers["X-Signature"] == expected
    assert req.headers["X-Api-Key"] == "cuq_op_key"
    assert "X-Idempotency-Key" not in req.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [503, 404])
async def test_get_pnl_raises_the_gateway_error(status):
    def handler(request):
        return httpx.Response(status, json={"error": {"code": "PNL_UNAVAILABLE", "message": "no rmu"}})

    with pytest.raises(ProxyError) as info:
        await _session(handler).get_pnl()
    assert info.value.code == "PNL_UNAVAILABLE"
    assert info.value.http_status == status


@pytest.mark.asyncio
async def test_get_pnl_non_json_is_unreachable():
    with pytest.raises(ProxyError) as info:
        await _session(lambda r: httpx.Response(502, content=b"<html>bad gateway</html>")).get_pnl()
    assert info.value.code == "PROXY_UNREACHABLE"


class _Container:
    def __init__(self, proxy):
        self.proxy = proxy


def _client(handler) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    container = _Container(_session(handler))
    app.dependency_overrides[current_container] = lambda: container
    return TestClient(app)


def test_route_returns_the_report():
    r = _client(lambda req: httpx.Response(200, json=REPORT)).get("/pnl")
    assert r.status_code == 200
    assert r.json() == REPORT


@pytest.mark.parametrize("gw_status,needle", [(404, "isn't configured"), (503, "Retry shortly")])
def test_route_maps_pnl_unavailable_to_503(gw_status, needle):
    def handler(req):
        return httpx.Response(gw_status, json={"error": {"code": "PNL_UNAVAILABLE", "message": "x"}})

    r = _client(handler).get("/pnl")
    assert r.status_code == 503
    assert needle in r.json()["detail"]


def test_route_maps_auth_failure_to_401():
    def handler(req):
        return httpx.Response(401, json={"error": {"code": "AUTH_FAILED", "message": "bad signature"}})

    r = _client(handler).get("/pnl")
    assert r.status_code == 401
    assert r.json()["detail"].startswith("AUTH_FAILED")


def test_route_explains_a_gateway_without_the_pnl_route():
    r = _client(lambda req: httpx.Response(404, json={"detail": "Not Found"})).get("/pnl")
    assert r.status_code == 503
    assert "no PnL route" in r.json()["detail"]
