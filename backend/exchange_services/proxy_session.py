"""ProxySession — the trading terminal's only credential.

The terminal holds no exchange keys. Every OKX call it makes travels through
the CU Quants Trading Gateway ("the Proxy"), which holds the club's single
vaulted OKX key, enforces the §4.2 action allowlist and the spot-only
instrument rule, and writes every request to an append-only audit log under
the terminal's own api_key_id.

REST (`call`) delegates to `proxy_client.ProxyClient`; the private
order-event WebSocket (`exchange_services/okx_order_stream.py`) delegates to
`proxy_client.websocket.ProxyWebSocketClient`. Both come from the shared
`cuq-proxy-client` SDK (also used by `xlrts` and `speedbyte`), so there is
one signing / handshake / error-classification implementation in play, not
one per consumer.

Credential type: **operator**. Each trader signs in to the terminal with
their own gateway operator credential (the four `proxy:` values from their
xlrts config.yaml), and gets their own `ProxySession` — built in
`routes/auth.py`, owned by their `auth.sessions.UserSession`. It must *not*
send `system_name` — `ProxyClient.for_operator` / `for_operator` is used, and
there is no `system_name` field here to get wrong. Every request is thereby
attributed in the gateway's audit log to the trader who made it.

Simulated vs. live is **not** a terminal setting any more. Whether an order
reaches OKX's demo environment or the real one is decided by `OKX_SIMULATED`
on the gateway the terminal points at (`CUQ_PROXY_URL`), with demo
credentials vaulted there. To test against OKX's simulated environment,
point `CUQ_PROXY_URL` at a gateway running in that mode.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx

from proxy_client import ProxyClient
from proxy_client.errors import ProxyError, ProxyUnreachableError, from_response
from proxy_client.signing import compute_signature

__all__ = ["ProxySession", "ProxyConfigError", "ProxyError"]


class ProxyConfigError(RuntimeError):
    """Raised when the server is missing configuration it needs."""


class ProxySession:
    """One signed-in trader's authenticated session against the Proxy.

    Built only at sign-in (`routes/auth.py`), from that trader's own
    credential, and handed to every service in their `ServiceContainer`.
    There is deliberately no other construction site: a component that could
    build its own session could be given someone else's credential, and the
    audit story depends on each request carrying the identity of the trader
    who made it.
    """

    #: How long to wait on a single Proxy call. The Proxy's own upstream
    #: timeout is shorter, so this only fires if the Proxy itself is wedged.
    DEFAULT_TIMEOUT = 15.0

    #: The gateway's PnL route (trading-gateway `proxy/pnl.py`). Not an
    #: exchange action, so it isn't `POST /v1/{exchange}` and the SDK's
    #: `acall` can't reach it.
    PNL_PATH = "/v1/rmu/pnl"
    #: The gateway's risk status route: RMU Core's kill switch, read-only.
    RISK_PATH = "/v1/rmu/risk"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        secret: str,
        operator_id: str,
        operator_name: str,
        timeout: float = DEFAULT_TIMEOUT,
        ws_url: str = "",
    ) -> None:
        self._base = base_url.rstrip("/")
        # An explicit wss:// base (server's CUQ_PROXY_WS_URL), or "" to let the
        # SDK derive it from base_url. Kept so a deployment cannot end up
        # with the REST and WS bases pointing at different hosts.
        self._ws_url = (ws_url or "").rstrip("/")
        self._api_key = api_key
        self._secret = secret
        self.operator_id = operator_id
        self.operator_name = operator_name
        self._client = ProxyClient.for_operator(
            base_url, api_key, secret, operator_id, operator_name, timeout=timeout
        )
        # For the RMU read routes only (PnL, risk status). Their success body is the RMU's report at the
        # top level, not the Proxy's usual `{"data": ...}` envelope.
        self._http = httpx.AsyncClient(timeout=timeout)

    def __repr__(self) -> str:  # never let the secret reach a traceback or log
        return f"<ProxySession {self.operator_id} via {self._base}>"

    __str__ = __repr__

    # ------------------------------------------------------------------
    # The one network call
    # ------------------------------------------------------------------

    async def call(
        self,
        exchange: str,
        action: str,
        payload: dict | None = None,
        *,
        idempotency_key: str = "",
    ) -> Any:
        """Run one action through the Proxy and return the venue's body.

        Returns the `data` field of the Proxy's envelope — i.e. exactly what
        the venue replied, unreshaped. For OKX that is the familiar
        `{"code": "0", "msg": "", "data": [...]}`, which is what lets every
        parser in `okx_service.py` stay exactly as it was.

        Raises a typed `proxy_client.errors.ProxyError` subclass on failure
        (`ExchangeError` for an OKX business rejection, carrying OKX's own
        `code`/`sMsg` under `.detail["body"]`; `AuthFailedError`,
        `RateLimitedError`, etc. for Proxy-level failures).
        """
        return await self._client.acall(
            exchange, action, payload or {}, idempotency_key=idempotency_key
        )

    async def get_pnl(self, group_by: str = "pair") -> dict[str, Any]:
        """The club's PnL report: `POST /v1/rmu/pnl` on the gateway, which
        passes RMU Core's `GET /v1/pnl` through unchanged.

        Signed exactly like every other request (the SDK's own
        `compute_signature`, over this path). Returns the RMU's JSON as-is:
        nothing here recomputes a number. Raises a `ProxyError` (code
        `PNL_UNAVAILABLE` when the gateway can't reach the RMU or the route
        isn't configured there).

        TODO: move into proxy-client as `get_pnl()` (trading-gateway ROADMAP)
        and call that instead.
        """
        return await self._signed_read(self.PNL_PATH, {"group_by": group_by})

    async def get_risk_status(self) -> dict[str, Any]:
        """The RMU's risk status: `POST /v1/rmu/risk` on the gateway, which
        returns `{"kill_switch": <RMU Core's GET /v1/kill-switch>}` unchanged.

        Signed like `get_pnl`. Raises a `ProxyError` (code
        `RISK_STATUS_UNAVAILABLE` when the gateway can't reach the RMU or the
        route isn't configured there).
        """
        return await self._signed_read(self.RISK_PATH, {})

    async def _signed_read(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """One signed `POST` to a gateway RMU read route; the body back as-is."""
        body = json.dumps({
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "payload": payload,
        }).encode()
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        headers = {
            "X-Api-Key": self._api_key,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": compute_signature(
                self._secret.encode("utf-8"), "POST", path, timestamp, nonce, body,
            ),
            "Content-Type": "application/json",
        }
        try:
            # `content=`, never `json=`: the bytes sent must be the bytes signed.
            response = await self._http.post(f"{self._base}{path}", content=body, headers=headers)
        except httpx.RequestError as exc:
            raise ProxyUnreachableError(str(exc)) from exc

        try:
            parsed = response.json()
        except ValueError:
            raise ProxyUnreachableError(f"HTTP {response.status_code} with a non-JSON body") from None
        if not isinstance(parsed, dict):
            raise ProxyUnreachableError(f"HTTP {response.status_code} with an unexpected JSON shape")
        if response.status_code >= 400 or "error" in parsed:
            err = parsed.get("error") or {}
            exc = from_response(
                err.get("code", f"HTTP_{response.status_code}"),
                err.get("message", "the Proxy rejected the request"),
                detail=err.get("detail"),
                request_id=err.get("request_id", ""),
            )
            exc.http_status = response.status_code
            raise exc
        return parsed

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pools. Called when the
        trader's session ends."""
        await self._client.aclose()
        self._client.close()
        await self._http.aclose()

    # ------------------------------------------------------------------
    # WebSocket — credential material for ProxyWebSocketClient
    # ------------------------------------------------------------------
    # The WS client owns the §5.2 handshake (signed with the same
    # `compute_signature` as REST); all it needs from here is the credential
    # material, read-only.

    @property
    def base_url(self) -> str:
        """The Proxy REST base, e.g. `https://proxy.example`. The WS client
        derives `wss://.../v1/{exchange}/ws` from this unless
        `ws_url_override` is set."""
        return self._base

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def secret(self) -> str:
        """The raw Proxy secret (str). The SDK encodes it when it signs."""
        return self._secret

    @property
    def ws_url_override(self) -> str:
        """An explicit `wss://` base (server's `CUQ_PROXY_WS_URL`), or `""` to
        derive it from `base_url`."""
        return self._ws_url
