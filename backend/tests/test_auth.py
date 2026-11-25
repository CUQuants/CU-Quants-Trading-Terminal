"""Sign-in, sessions and the auth guard on every route.

The gateway is a fake behind `httpx.MockTransport` that checks the HMAC
signature exactly as trading-gateway does (`proxy_client.signing`), so a
login only succeeds when the four fields really sign a valid request.
"""

import json
import os
import sys

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("CUQ_PROXY_URL", "http://gw.test")  # app.py builds a default app at import

from proxy_client.signing import compute_signature

import routes.auth as auth_routes
from app import create_app
from auth import SESSION_COOKIE
from auth.sessions import SessionStore
from auth.settings import AuthSettings
from auth.throttle import LoginThrottle, SlidingWindow
from exchange_services.proxy_session import ProxySession

ALICE = {"api_key": "cuq_op_AAAAAAAAAAAAAAAA1", "api_secret": "c2VjcmV0LWFsaWNl",
         "operator_id": "cuq-016", "operator_name": "Alice Trader"}
BOB = {"api_key": "cuq_op_BBBBBBBBBBBBBBBB2", "api_secret": "c2VjcmV0LWJvYg==",
       "operator_id": "cuq-017", "operator_name": "Bob Trader"}


class FakeGateway:
    """Knows two credentials; answers like trading-gateway's auth stage."""

    def __init__(self):
        self.keys = {c["api_key"]: (c["api_secret"], c["operator_id"]) for c in (ALICE, BOB)}
        self.requests: list[httpx.Request] = []
        self.revoked: set[str] = set()
        self.unreachable = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("down", request=request)
        key = request.headers.get("X-Api-Key", "")
        body = request.content
        known = self.keys.get(key)
        ok = known is not None and request.headers.get("X-Signature") == compute_signature(
            known[0].encode(), "POST", request.url.path,
            request.headers["X-Timestamp"], request.headers["X-Nonce"], body,
        ) and json.loads(body).get("operator_id") == known[1]
        if not ok:
            return httpx.Response(401, json={"error": {
                "code": "AUTH_FAILED", "message": "authentication failed", "request_id": "rid-401"}})
        if key in self.revoked:
            return httpx.Response(401, json={"error": {
                "code": "CREDENTIAL_EXPIRED", "message": "revoked", "request_id": "rid-exp"}})
        return httpx.Response(200, json={"data": {"error": [], "result": {"unixtime": 1}}})


@pytest.fixture
def gateway(monkeypatch):
    gw = FakeGateway()

    class MockedProxySession(ProxySession):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._client._aclient = httpx.AsyncClient(transport=httpx.MockTransport(gw.handle))

    monkeypatch.setattr(auth_routes, "ProxySession", MockedProxySession)
    return gw


@pytest.fixture
def client(gateway):
    app = create_app(AuthSettings(proxy_url="http://gw.test", cookie_secure=False))
    with TestClient(app) as c:
        yield c


def login(client, creds=ALICE, **overrides):
    return client.post("/auth/login", json={**creds, **overrides})


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------


def test_login_sets_an_httponly_strict_cookie_and_me_works(client, gateway):
    r = login(client)

    assert r.status_code == 200
    assert r.json() == {"operator_id": "cuq-016", "operator_name": "Alice Trader"}
    set_cookie = r.headers["set-cookie"]
    assert SESSION_COOKIE in set_cookie
    assert "HttpOnly" in set_cookie and "samesite=strict" in set_cookie.lower()
    assert ALICE["api_secret"] not in set_cookie  # the cookie is an opaque id only

    # Verified with one signed get_server_time on `kraken`, as xlrts does.
    sent = json.loads(gateway.requests[0].content)
    assert gateway.requests[0].url.path == "/v1/kraken"
    assert sent["action"] == "get_server_time"
    assert sent["operator_id"] == "cuq-016" and sent["operator_name"] == "Alice Trader"
    assert ALICE["api_secret"] not in gateway.requests[0].content.decode()

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["operator_id"] == "cuq-016"


def test_cookie_is_secure_by_default(gateway):
    app = create_app(AuthSettings(proxy_url="http://gw.test"))
    with TestClient(app) as c:
        r = login(c)
    assert r.status_code == 200
    assert "Secure" in r.headers["set-cookie"]


def test_fields_are_trimmed(client):
    padded = {k: f"  {v}  " for k, v in ALICE.items()}
    assert login(client, padded).status_code == 200


@pytest.mark.parametrize("field,value", [
    ("api_secret", "d3JvbmctLXNlY3JldA=="),           # wrong secret
    ("operator_id", "cuq-999"),                        # key owned by someone else
    ("api_key", "cuq_op_ZZZZZZZZZZZZZZZZ9"),           # unknown key
])
def test_gateway_rejection_is_a_401_with_the_request_id(client, field, value):
    r = login(client, **{field: value})

    assert r.status_code == 401
    detail = r.json()["detail"]
    assert detail["request_id"] == "rid-401"
    assert "API key, secret and operator ID" in detail["message"]
    assert SESSION_COOKIE not in r.headers.get("set-cookie", "")
    assert client.get("/auth/me").status_code == 401


def test_revoked_credential_says_so(client, gateway):
    gateway.revoked.add(ALICE["api_key"])
    r = login(client)
    assert r.status_code == 401
    assert "revoked" in r.json()["detail"]["message"]


def test_unreachable_gateway_is_503(client, gateway):
    gateway.unreachable = True
    assert login(client).status_code == 503


@pytest.mark.parametrize("field,value", [
    ("api_key", ""),
    ("api_key", "not-a-key"),
    ("api_secret", ""),
    ("api_secret", "has a space"),
    ("operator_id", "016"),
    ("operator_id", ""),
    ("operator_name", "   "),
    ("operator_name", "x" * 101),
])
def test_malformed_fields_are_400_and_never_reach_the_gateway(client, gateway, field, value):
    r = login(client, **{field: value})

    assert r.status_code == 400
    assert r.json()["detail"]["field"] == field
    assert gateway.requests == []


def test_repeated_failures_are_throttled_before_the_gateway(client, gateway):
    for _ in range(5):
        assert login(client, api_secret="d3JvbmctLXNlY3JldA==").status_code == 401
    sent = len(gateway.requests)

    r = login(client)  # even the right secret, until the window passes
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert len(gateway.requests) == sent


def test_global_throttle_caps_failures_across_all_clients():
    now = [0.0]
    t = LoginThrottle(clock=lambda: now[0])
    for i in range(6):
        t.record_failure(f"10.0.0.{i}")  # six different traders, one failure each
    assert t.retry_after("10.0.0.99") > 0  # a seventh IP must wait too
    now[0] = 61
    assert t.retry_after("10.0.0.99") == 0


def test_sliding_window_forgets_old_failures():
    now = [0.0]
    w = SlidingWindow(2, 10, clock=lambda: now[0])
    w.record("k"); w.record("k")
    assert w.retry_after("k") == pytest.approx(10)
    now[0] = 10.5
    assert w.retry_after("k") == 0


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def test_logout_ends_the_session(client):
    login(client)
    sid = client.cookies.get(SESSION_COOKIE)

    r = client.post("/auth/logout")
    assert r.status_code == 204
    client.cookies.set(SESSION_COOKIE, sid)  # replaying the old id must not work
    assert client.get("/auth/me").status_code == 401
    assert len(client.app.state.sessions) == 0


def test_two_traders_get_isolated_sessions(client):
    login(client, ALICE)
    alice_sid = client.cookies.get(SESSION_COOKIE)
    client.cookies.clear()
    login(client, BOB)
    bob_sid = client.cookies.get(SESSION_COOKIE)

    store = client.app.state.sessions
    assert len(store) == 2
    a, b = store._sessions[alice_sid], store._sessions[bob_sid]
    assert a.container is not b.container and a.relay is not b.relay
    assert a.container.proxy.operator_id == "cuq-016"
    assert b.container.proxy.operator_id == "cuq-017"

    client.cookies.set(SESSION_COOKIE, alice_sid)
    assert client.get("/auth/me").json()["operator_id"] == "cuq-016"


def test_signing_in_again_replaces_this_browsers_session(client):
    login(client)
    login(client)
    assert len(client.app.state.sessions) == 1


@pytest.mark.asyncio
async def test_sessions_expire_when_idle_and_at_max_age():
    class Closable:
        closed = False

        async def aclose(self):
            Closable.closed = True

        async def shutdown(self):
            pass

    now = [0.0]
    store = SessionStore(idle_seconds=10, max_seconds=30, clock=lambda: now[0])
    s = store.add(Closable(), "cuq-016", "Alice")
    s.relay = Closable()

    now[0] = 9
    assert await store.get(s.session_id) is s  # touches last_seen
    now[0] = 18
    assert await store.get(s.session_id) is s
    now[0] = 27
    assert await store.get(s.session_id) is s
    now[0] = 31  # past max age despite activity
    assert await store.get(s.session_id) is None
    assert Closable.closed


@pytest.mark.asyncio
async def test_sweep_closes_idle_sessions():
    class Closable:
        async def aclose(self):
            pass

        async def shutdown(self):
            pass

    now = [0.0]
    store = SessionStore(idle_seconds=10, max_seconds=100, clock=lambda: now[0])
    s = store.add(Closable(), "cuq-016", "Alice")
    s.relay = Closable()
    now[0] = 11
    assert await store.sweep() == 1
    assert len(store) == 0


# ---------------------------------------------------------------------------
# The guard on every trading route
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", [
    ("GET", "/orders/okx?pair=BTC/USD"),
    ("GET", "/orders/okx"),
    ("POST", "/orders/okx"),
    ("DELETE", "/orders/okx/123?pair=BTC/USD"),
    ("GET", "/trades/okx"),
    ("GET", "/account/cash/okx?pair=BTC/USD"),
    ("GET", "/account/positions/okx"),
    ("GET", "/account/balances/okx"),
    ("GET", "/pnl"),
    ("GET", "/reporting/health"),
    ("GET", "/reporting/logs"),
])
def test_routes_require_a_session(client, method, path):
    r = client.request(method, path, json={} if method == "POST" else None)
    assert r.status_code == 401
    assert r.json()["detail"].startswith("NOT_SIGNED_IN")


def test_health_check_stays_public(client):
    assert client.get("/").json() == {"status": "ok"}


def test_order_ws_without_a_session_is_closed_4401(client):
    with client.websocket_connect("/orders/kraken") as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_text()
    assert info.value.code == 4401


def test_order_ws_with_a_session_connects(client):
    login(client)
    # Kraken's order stream is a no-op, so this opens nothing upstream.
    with client.websocket_connect("/orders/kraken") as ws:
        ws.send_text("ping")
    sid = client.cookies.get(SESSION_COOKIE)
    assert client.app.state.sessions._sessions[sid].relay is not None


def test_order_ws_from_another_site_is_refused_even_with_the_cookie(client):
    login(client)
    with client.websocket_connect("/orders/kraken", headers={"Origin": "https://evil.example"}) as ws:
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_text()
    assert info.value.code == 4401


def test_cross_site_writes_are_refused(client, gateway):
    r = client.post("/auth/login", json=ALICE, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert gateway.requests == []


def test_same_origin_writes_are_allowed(client):
    r = client.post("/auth/login", json=ALICE, headers={"Origin": "http://testserver"})
    assert r.status_code == 200


def test_a_listed_extra_origin_is_allowed(gateway):
    app = create_app(AuthSettings(proxy_url="http://gw.test", cookie_secure=False,
                                  allowed_origins=frozenset({"https://ok.example"})))
    with TestClient(app) as c:
        r = c.post("/auth/login", json=ALICE, headers={"Origin": "https://ok.example"})
    assert r.status_code == 200


def test_a_credential_revoked_mid_session_signs_the_trader_out(client, gateway, monkeypatch):
    login(client)
    gateway.revoked.add(ALICE["api_key"])
    sid = client.cookies.get(SESSION_COOKIE)
    container = client.app.state.sessions._sessions[sid].container
    # Route the trader's own session through the fake gateway too.
    container.proxy._client._aclient = httpx.AsyncClient(transport=httpx.MockTransport(gateway.handle))

    r = client.get("/account/balances/okx")
    assert r.status_code == 401
    assert client.get("/auth/me").status_code == 401
