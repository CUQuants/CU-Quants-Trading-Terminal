"""Failed-login throttling, in front of the gateway's own.

The gateway rate-limits failed authentication **per source IP** (a bucket of
8, refilling at 0.2/s — trading-gateway `proxy/config.py`). Every login the
terminal checks reaches the gateway from the terminal's single address, so
without a limit here one trader mistyping their secret repeatedly would drain
that bucket and lock *every* trader out of the terminal.

Two sliding windows:

* per client IP — slows down one browser (5 failures / 15 min);
* global — keeps the total failure rate this server causes well under the
  gateway's refill rate (6 failures / 60 s vs. 12 tokens/min refilled), so the
  shared bucket never empties.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, Deque, Dict


class SlidingWindow:
    def __init__(self, max_failures: int, window_seconds: float,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: Dict[str, Deque[float]] = {}

    def _prune(self, key: str, now: float) -> Deque[float] | None:
        hits = self._hits.get(key)
        if hits is None:
            return None
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return None
        return hits

    def retry_after(self, key: str) -> float:
        """Seconds until `key` may try again; 0 when it may try now."""
        now = self._clock()
        hits = self._prune(key, now)
        if hits is None or len(hits) < self.max_failures:
            return 0.0
        return max(0.0, hits[0] + self.window_seconds - now)

    def record(self, key: str) -> None:
        now = self._clock()
        self._prune(key, now)
        self._hits.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


GLOBAL_KEY = "*"


class LoginThrottle:
    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 per_ip: tuple[int, float] = (5, 15 * 60),
                 global_: tuple[int, float] = (6, 60)) -> None:
        self._per_ip = SlidingWindow(*per_ip, clock=clock)
        self._global = SlidingWindow(*global_, clock=clock)

    def retry_after(self, ip: str) -> float:
        return max(self._per_ip.retry_after(ip), self._global.retry_after(GLOBAL_KEY))

    def record_failure(self, ip: str) -> None:
        self._per_ip.record(ip)
        self._global.record(GLOBAL_KEY)

    def record_success(self, ip: str) -> None:
        self._per_ip.reset(ip)
