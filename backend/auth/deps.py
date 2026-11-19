"""FastAPI dependencies: who is signed in, and is this request same-origin."""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, WebSocket
from starlette.requests import HTTPConnection

from exchange_services.service_container import ServiceContainer

from .sessions import SessionStore, UserSession

SESSION_COOKIE = "cuq_session"
#: Close code for a WebSocket refused for want of a session (mirrors the gateway's 4401).
WS_UNAUTHORIZED = 4401

NOT_SIGNED_IN = "NOT_SIGNED_IN: sign in to the terminal first."


def origin_allowed(conn: HTTPConnection) -> bool:
    """True unless the request carries an `Origin` from another site.

    Same-origin (the Origin's host matches the Host header the browser sent)
    is always allowed: production (Caddy keeps Host) and the Vite dev proxy
    (left with `changeOrigin: false`) are both same-origin. Anything else must
    be listed in TERMINAL_ALLOWED_ORIGINS. A request with no Origin at all
    (curl, server-to-server) carries no browser cookies by accident, so it is
    left to the cookie check.
    """
    origin = conn.headers.get("origin")
    if not origin:
        return True
    origin = origin.rstrip("/")
    settings = getattr(conn.app.state, "auth_settings", None)
    if settings is not None and origin in settings.allowed_origins:
        return True
    host = conn.headers.get("host", "")
    return bool(host) and urlsplit(origin).netloc.lower() == host.lower()


def _store(conn: HTTPConnection) -> SessionStore:
    return conn.app.state.sessions


async def current_session(request: Request) -> UserSession:
    session = await _store(request).get(request.cookies.get(SESSION_COOKIE))
    if session is None:
        raise HTTPException(status_code=401, detail=NOT_SIGNED_IN)
    return session


async def current_container(session: UserSession = Depends(current_session)) -> ServiceContainer:
    return session.container


async def ws_session(websocket: WebSocket) -> UserSession | None:
    """The signed-in session behind a WebSocket, or None. Checks Origin first:
    browsers send cookies on cross-site WebSocket handshakes, so without this
    any web page could open a socket as the trader."""
    if not origin_allowed(websocket):
        return None
    return await _store(websocket).get(websocket.cookies.get(SESSION_COOKIE))
