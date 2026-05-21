"""Shared pytest fixtures and path setup for the backend test suite.

Importing this module via pytest's auto-discovery does two things:

1. Puts ``terminal/backend`` on ``sys.path`` so tests can do
   ``from exchange_services.okx_service import OkxService`` without each
   test file having to fiddle with ``sys.path`` itself.
2. Provides per-exchange service fixtures used by the unit and
   integration tests.
"""

from __future__ import annotations

import os
import sys

import pytest

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from exchange_services.gemini_service import GeminiService  # noqa: E402
from exchange_services.kraken_service import KrakenService  # noqa: E402
from exchange_services.okx_service import OkxService  # noqa: E402


@pytest.fixture
def okx_svc() -> OkxService:
    return OkxService(base_url="https://us.okx.com", simulated=True)


@pytest.fixture
def kraken_svc() -> KrakenService:
    # Note: Kraken has no paper-trading sandbox; ``simulated=True`` is a
    # no-op on this service today. Integration tests must self-skip when
    # KRAKEN_API_KEY is unset to avoid touching the live account.
    return KrakenService(base_url="https://api.kraken.com", simulated=True)


@pytest.fixture
def gemini_svc() -> GeminiService:
    # Defaults to production. Gemini also exposes a paper-trading sandbox
    # at api.sandbox.gemini.com; swap the URL here if you want integration
    # tests to run against the sandbox instead of live.
    return GeminiService(base_url="https://api.gemini.com", simulated=True)
