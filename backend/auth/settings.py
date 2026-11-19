"""Server-side settings for sign-in. Read once, at startup, from the env.

None of these is a trader credential. Traders bring their own four gateway
values (api_key / api_secret / operator_id / operator_name) to the login page;
the server only needs to know *where* the gateway is.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise RuntimeError(f"{name} must be a number, got {raw!r}") from None
    if value <= 0:
        raise RuntimeError(f"{name} must be positive, got {raw!r}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise RuntimeError(f"{name} must be true or false, got {raw!r}")


@dataclass(frozen=True)
class AuthSettings:
    #: The gateway's REST base. On the server box this is the loopback
    #: `http://127.0.0.1:8080`; locally, the public gateway URL.
    proxy_url: str
    #: Explicit `wss://` base, or "" to derive it from `proxy_url`.
    proxy_ws_url: str = ""
    #: The audit-reporting API, or "" when it isn't deployed (Reporting tab → 503).
    reporting_url: str = ""
    #: Mark the session cookie `Secure`. Only turn off for plain-http local dev.
    cookie_secure: bool = True
    #: A session unused this long is signed out.
    idle_seconds: float = 12 * 3600
    #: No session outlives this, however active.
    max_seconds: float = 24 * 3600
    #: Extra origins allowed besides the request's own (same-origin is always
    #: allowed). Normally empty: production and the Vite dev proxy are both
    #: same-origin.
    allowed_origins: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_env(cls) -> "AuthSettings":
        proxy_url = _env("CUQ_PROXY_URL")
        if not proxy_url:
            raise RuntimeError(
                "CUQ_PROXY_URL is not set. The terminal signs traders in against "
                "the CU Quants Trading Gateway and needs to know where it is."
            )
        origins = frozenset(
            o.strip().rstrip("/") for o in _env("TERMINAL_ALLOWED_ORIGINS").split(",") if o.strip()
        )
        return cls(
            proxy_url=proxy_url.rstrip("/"),
            proxy_ws_url=_env("CUQ_PROXY_WS_URL").rstrip("/"),
            reporting_url=_env("CUQ_REPORTING_URL").rstrip("/"),
            cookie_secure=_env_bool("TERMINAL_COOKIE_SECURE", True),
            idle_seconds=_env_float("TERMINAL_SESSION_IDLE_HOURS", 12) * 3600,
            max_seconds=_env_float("TERMINAL_SESSION_MAX_HOURS", 24) * 3600,
            allowed_origins=origins,
        )
