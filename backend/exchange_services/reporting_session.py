"""ReportingSession — the terminal's session against the audit-reporting API.

`proxy_admin.reporting` (`trading-gateway`) is a **second, separate**
service from the Proxy `ProxySession` talks to: its own process, its own
default port (`:8090` against the Proxy's `:8080`), no reverse-proxy route.
It reuses the exact credential the trader signed in to the terminal with —
per `trading-gateway/DEV_GATEWAY.md`, the reporting routes accept any
operator with `admin_role='auditor'`, so no second credential is issued for
this. Only the base URL differs: the server's `CUQ_REPORTING_URL`.

Unlike `ProxySession`, this is **optional**: a deployment that hasn't stood
up the reporting service leaves `CUQ_REPORTING_URL` unset, sign-in builds no
`ReportingSession`, and the Reporting tab answers 503 instead.
"""

from __future__ import annotations

from typing import Any

from proxy_client import ReportingClient

from .proxy_session import ProxyConfigError

__all__ = ["ReportingSession", "ProxyConfigError"]


class ReportingSession:
    """One signed-in trader's session against the audit-reporting API.

    Built at sign-in alongside their `ProxySession`, from the same
    credential (`routes/auth.py`).
    """

    DEFAULT_TIMEOUT = 15.0

    def __init__(
        self,
        base_url: str,
        api_key: str,
        secret: str,
        operator_id: str,
        operator_name: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base = base_url.rstrip("/")
        self.operator_id = operator_id
        self.operator_name = operator_name
        self._client = ReportingClient.for_operator(
            base_url, api_key, secret, operator_id, operator_name, timeout=timeout
        )

    def __repr__(self) -> str:  # never let the secret reach a traceback or log
        return f"<ReportingSession {self.operator_id} via {self._base}>"

    __str__ = __repr__

    # ------------------------------------------------------------------
    # The four endpoints — real async I/O, matching ProxySession.call's use
    # of acall rather than call() run in a thread.
    # ------------------------------------------------------------------

    async def log_health(self) -> dict[str, Any]:
        return await self._client.alog_health()

    async def unresolved_orders(self) -> list[dict[str, Any]]:
        return await self._client.aunresolved_orders()

    async def auth_failures(self) -> list[dict[str, Any]]:
        return await self._client.aauth_failures()

    async def query_logs(self, **filters: Any) -> dict[str, Any]:
        return await self._client.aquery_logs(**filters)

    async def aclose(self) -> None:
        await self._client.aclose()
        self._client.close()
