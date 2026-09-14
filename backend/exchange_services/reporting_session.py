"""ReportingSession — the terminal's session against the audit-reporting API.

`proxy_admin.reporting` (`trading-gateway`) is a **second, separate**
service from the Proxy `ProxySession` talks to: its own process, its own
default port (`:8090` against the Proxy's `:8080`), no reverse-proxy route.
It reuses the exact same operator credential the terminal already holds for
trading (`CUQ_PROXY_API_KEY`/`_SECRET`/`_OPERATOR_ID`/`_OPERATOR_NAME`) —
per `trading-gateway/DEV_GATEWAY.md`, the same seeded operator that can
place orders is already granted `admin_role='auditor'`, so no second
credential is issued for this. Only the base URL differs, hence the one new
`CUQ_REPORTING_URL` variable.

Unlike `ProxySession`, this is **optional**: a deployment that hasn't stood
up the reporting service yet should keep trading normally rather than fail
to boot. `ServiceContainer` is responsible for catching `ProxyConfigError`
from `from_env()` and treating a missing reporting session as "not
configured" rather than a startup failure — see its docstring.
"""

from __future__ import annotations

import os
from typing import Any

from proxy_client import ReportingClient

from .proxy_session import ProxyConfigError

__all__ = ["ReportingSession", "ProxyConfigError"]


class ReportingSession:
    """The terminal's authenticated session against the audit-reporting API.

    One instance is built at startup in `ServiceContainer`, mirroring
    `ProxySession` — a component that could build its own session could be
    given its own credential, and the audit story depends on there being
    exactly one identity per process.
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

    @classmethod
    def from_env(cls, timeout: float = DEFAULT_TIMEOUT) -> "ReportingSession":
        """Build from the environment. Reuses the terminal's existing
        `CUQ_PROXY_*` operator credential — only `CUQ_REPORTING_URL` is new."""
        required = {
            "CUQ_REPORTING_URL": os.getenv("CUQ_REPORTING_URL", ""),
            "CUQ_PROXY_API_KEY": os.getenv("CUQ_PROXY_API_KEY", ""),
            "CUQ_PROXY_SECRET": os.getenv("CUQ_PROXY_SECRET", ""),
            "CUQ_PROXY_OPERATOR_ID": os.getenv("CUQ_PROXY_OPERATOR_ID", ""),
            "CUQ_PROXY_OPERATOR_NAME": os.getenv("CUQ_PROXY_OPERATOR_NAME", ""),
        }
        missing = sorted(name for name, value in required.items() if not value.strip())
        if missing:
            raise ProxyConfigError(
                "The reporting API needs: "
                f"{', '.join(missing)}. Ask the club liaison for an operator "
                "credential with admin_role='auditor' (see trading-gateway's "
                "NEW-USER.md and DEV_GATEWAY.md)."
            )
        return cls(
            base_url=required["CUQ_REPORTING_URL"].strip(),
            api_key=required["CUQ_PROXY_API_KEY"].strip(),
            secret=required["CUQ_PROXY_SECRET"].strip(),
            operator_id=required["CUQ_PROXY_OPERATOR_ID"].strip(),
            operator_name=required["CUQ_PROXY_OPERATOR_NAME"].strip(),
            timeout=timeout,
        )

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
