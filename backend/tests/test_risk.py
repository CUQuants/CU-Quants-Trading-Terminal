"""Risk status: `ProxySession.get_risk_status` (the signed `POST /v1/rmu/risk`)
and the terminal's `GET /risk` route. The gateway is an `httpx.MockTransport`."""

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
from routes.risk import router

SECRET = "c2VjcmV0LXNlY3JldA=="
STATUS = {
    "kill_switch": {
        "enabled": True, "tripped": False, "trip_reason": None, "trip_persisted": True,
        "pnl": "-120.50", "threshold": "1000",
        "baseline_nav": "50000.00", "baseline_ts": "2026-11-09T00:00:00+00:00",
        "baseline_source": "config", "baseline_persisted": True,
        "nav": "49879.50", "nav_as_of": "2026-11-24T15:00:00+00:00",
    }
}


def _session(handler) -> ProxySession:
    s = ProxySession("http://gw.test", "cuq_op_key", SECRET, "cuq-001", "Sammy")
    s._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return s


@pytest.mark.asyncio
async def test_get_risk_status_signs_the_risk_path_and_returns_it_unchanged():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=STATUS)

    assert await _session(handler).get_risk_status() == STATUS
    req = seen[0]
    assert req.method == "POST" and req.url.path == "/v1/rmu/risk"
    body = req.content
    assert json.loads(body) == {"operator_id": "cuq-001", "operator_name": "Sammy", "payload": {}}
    expected = compute_signature(SECRET.encode(), "POST", "/v1/rmu/risk",
                                 req.headers["X-Timestamp"], req.headers["X-Nonce"], body)
    assert req.headers["X-Signature"] == expected
    assert "X-Idempotency-Key" not in req.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [503, 404])
async def test_get_risk_status_raises_the_gateway_error(status):
    def handler(request):
        return httpx.Response(status, json={"error": {"code": "RISK_STATUS_UNAVAILABLE", "message": "no rmu"}})

    with pytest.raises(ProxyError) as info:
        await _session(handler).get_risk_status()
    assert info.value.code == "RISK_STATUS_UNAVAILABLE"
    assert info.value.http_status == status


class _Container:
    def __init__(self, proxy):
        self.proxy = proxy


def _client(handler) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    container = _Container(_session(handler))
    app.dependency_overrides[current_container] = lambda: container
    return TestClient(app)


def test_route_returns_the_status():
    r = _client(lambda req: httpx.Response(200, json=STATUS)).get("/risk")
    assert r.status_code == 200 and r.json() == STATUS


@pytest.mark.parametrize("gw_status,needle", [(404, "isn't configured"), (503, "Retry shortly")])
def test_route_maps_risk_status_unavailable_to_503(gw_status, needle):
    def handler(req):
        return httpx.Response(gw_status, json={"error": {"code": "RISK_STATUS_UNAVAILABLE", "message": "x"}})

    r = _client(handler).get("/risk")
    assert r.status_code == 503 and needle in r.json()["detail"]


def test_route_maps_auth_failure_to_401():
    def handler(req):
        return httpx.Response(401, json={"error": {"code": "AUTH_FAILED", "message": "bad signature"}})

    r = _client(handler).get("/risk")
    assert r.status_code == 401 and r.json()["detail"].startswith("AUTH_FAILED")


def test_route_explains_a_gateway_without_the_risk_route():
    r = _client(lambda req: httpx.Response(404, json={"detail": "Not Found"})).get("/risk")
    assert r.status_code == 503 and "no risk status route" in r.json()["detail"]
