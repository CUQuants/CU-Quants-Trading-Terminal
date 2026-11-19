"""Signed-in traders, held in this process's memory only.

The gateway has no sessions or tokens: every request is HMAC-signed with the
trader's secret. So once a trader signs in, the terminal must keep that secret
for as long as they stay signed in. It lives here, inside that trader's
`ProxySession`, and nowhere else: it is never written to disk, never sent back
to the browser, and gone when the process restarts (everyone signs in again).

The browser holds only an opaque, random session id in an HttpOnly cookie.

Each `UserSession` owns its own `ServiceContainer` (its own gateway identity,
so every request in the gateway's audit log names the real trader) and its
own `OrderEventRelay` (so traders never see one another's order events).

The store is per-process: run uvicorn with exactly one worker.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable, Dict

from exchange_services.service_container import ServiceContainer
from order_event_relay import OrderEventRelay

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    session_id: str
    operator_id: str
    operator_name: str
    container: ServiceContainer
    relay: OrderEventRelay
    created_at: float
    last_seen: float
    _closed: bool = field(default=False, repr=False)

    def __repr__(self) -> str:  # the id is a bearer credential: never log it whole
        return f"<UserSession {self.operator_id} {self.session_id[:6]}…>"

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.relay.shutdown()
        finally:
            await self.container.aclose()


class SessionStore:
    def __init__(self, idle_seconds: float, max_seconds: float,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.idle_seconds = idle_seconds
        self.max_seconds = max_seconds
        self._clock = clock
        self._sessions: Dict[str, UserSession] = {}

    def __len__(self) -> int:
        return len(self._sessions)

    def add(self, container: ServiceContainer, operator_id: str, operator_name: str) -> UserSession:
        now = self._clock()
        session = UserSession(
            session_id=secrets.token_urlsafe(32),
            operator_id=operator_id,
            operator_name=operator_name,
            container=container,
            relay=OrderEventRelay(container, label=operator_id),
            created_at=now,
            last_seen=now,
        )
        self._sessions[session.session_id] = session
        logger.info("Signed in: %s (%d active)", operator_id, len(self._sessions))
        return session

    def _expired(self, session: UserSession, now: float) -> bool:
        return (now - session.last_seen > self.idle_seconds
                or now - session.created_at > self.max_seconds)

    async def get(self, session_id: str | None) -> UserSession | None:
        """The live session for this id, touching its idle timer; None if
        unknown or expired (an expired one is closed on the way out)."""
        if not session_id:
            return None
        session = self._sessions.get(session_id)
        if session is None:
            return None
        now = self._clock()
        if self._expired(session, now):
            await self.destroy(session_id, reason="expired")
            return None
        session.last_seen = now
        return session

    async def destroy(self, session_id: str | None, reason: str = "signed out") -> None:
        if not session_id:
            return
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        logger.info("Session ended (%s): %s (%d active)", reason, session.operator_id, len(self._sessions))
        try:
            await session.aclose()
        except Exception:
            logger.exception("Error closing session for %s", session.operator_id)

    async def sweep(self) -> int:
        now = self._clock()
        doomed = [sid for sid, s in self._sessions.items() if self._expired(s, now)]
        for sid in doomed:
            await self.destroy(sid, reason="expired")
        return len(doomed)

    async def run_sweeper(self, interval: float = 60.0) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await self.sweep()
            except Exception:
                logger.exception("Session sweep failed")

    async def close_all(self) -> None:
        for sid in list(self._sessions):
            await self.destroy(sid, reason="shutdown")
