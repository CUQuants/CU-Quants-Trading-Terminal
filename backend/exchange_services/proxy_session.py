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

Credential type: **operator**. The terminal authenticates as a person
(whoever the deployment's `CUQ_PROXY_OPERATOR_*` names), so it must *not*
send `system_name` — `ProxyClient.for_operator` / `for_operator` is used, and
there is no `system_name` field here to get wrong. Every request the
terminal makes is attributed to that one operator in the audit log; that is
a deliberate continuation of how the terminal held one key set before.

Simulated vs. live is **not** a terminal setting any more. Whether an order
reaches OKX's demo environment or the real one is decided by `OKX_SIMULATED`
on the gateway this session points at (`CUQ_PROXY_URL`), with demo
credentials vaulted there. To test against OKX's simulated environment,
point `CUQ_PROXY_URL` at a gateway running in that mode.
"""

from __future__ import annotations

import os
from typing import Any

from proxy_client import ProxyClient
from proxy_client.errors import ProxyError

__all__ = ["ProxySession", "ProxyConfigError", "ProxyError"]


class ProxyConfigError(RuntimeError):
    """Raised when the environment is missing what a ProxySession needs.

    Names every missing variable at once, because discovering them one
    failed startup at a time is a bad way to spend a morning.
    """


class ProxySession:
    """The terminal's authenticated session against the Proxy.

    One instance is built at startup in `ServiceContainer` and handed to
    every service that needs to reach OKX. There is deliberately no second
    construction site: a component that could build its own session could be
    given its own credential, and the audit story depends on there being
    exactly one identity per process.
    """

    #: How long to wait on a single Proxy call. The Proxy's own upstream
    #: timeout is shorter, so this only fires if the Proxy itself is wedged.
    DEFAULT_TIMEOUT = 15.0

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
        # An explicit wss:// base (from CUQ_PROXY_WS_URL), or "" to let the
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

    def __repr__(self) -> str:  # never let the secret reach a traceback or log
        return f"<ProxySession {self.operator_id} via {self._base}>"

    __str__ = __repr__

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, timeout: float = DEFAULT_TIMEOUT) -> "ProxySession":
        """Build from the environment. The only place the secret is read."""
        required = {
            "CUQ_PROXY_URL": os.getenv("CUQ_PROXY_URL", ""),
            "CUQ_PROXY_API_KEY": os.getenv("CUQ_PROXY_API_KEY", ""),
            "CUQ_PROXY_SECRET": os.getenv("CUQ_PROXY_SECRET", ""),
            "CUQ_PROXY_OPERATOR_ID": os.getenv("CUQ_PROXY_OPERATOR_ID", ""),
            "CUQ_PROXY_OPERATOR_NAME": os.getenv("CUQ_PROXY_OPERATOR_NAME", ""),
        }
        missing = sorted(name for name, value in required.items() if not value.strip())
        if missing:
            raise ProxyConfigError(
                "The trading terminal reaches OKX only through the CU Quants "
                f"Proxy and cannot start without: {', '.join(missing)}. Ask the "
                "club liaison for an operator credential (see trading-gateway's "
                "NEW-USER.md)."
            )
        return cls(
            base_url=required["CUQ_PROXY_URL"].strip(),
            api_key=required["CUQ_PROXY_API_KEY"].strip(),
            secret=required["CUQ_PROXY_SECRET"].strip(),
            operator_id=required["CUQ_PROXY_OPERATOR_ID"].strip(),
            operator_name=required["CUQ_PROXY_OPERATOR_NAME"].strip(),
            timeout=timeout,
            # Normally empty, so the WebSocket base is derived from the REST
            # URL and the two cannot drift apart.
            ws_url=os.getenv("CUQ_PROXY_WS_URL", "").strip(),
        )

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

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pools. Called from the app's
        lifespan teardown."""
        await self._client.aclose()
        self._client.close()

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
        """An explicit `wss://` base from `CUQ_PROXY_WS_URL`, or `""` to
        derive it from `base_url`."""
        return self._ws_url
