"""Unit tests for ReportingSession.from_env() and its optional wiring into
ServiceContainer.

Unlike the other exchange_services tests, these don't stub a proxy — the
behavior worth guarding here is the env-var validation itself and the
"missing config must not crash the app" contract, not any request/response
shaping (ReportingSession has none; it delegates straight to
proxy_client.ReportingClient).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.reporting_session import ProxyConfigError, ReportingSession
from exchange_services.service_container import ServiceContainer

REQUIRED_VARS = (
    "CUQ_REPORTING_URL",
    "CUQ_PROXY_API_KEY",
    "CUQ_PROXY_SECRET",
    "CUQ_PROXY_OPERATOR_ID",
    "CUQ_PROXY_OPERATOR_NAME",
)


def _set_all(monkeypatch, **overrides):
    """Set every required var to a valid placeholder, then apply overrides
    (a value of None deletes that var instead of setting it) — so each test
    is explicit about what it's missing, regardless of a real backend/.env
    on disk."""
    values = {
        "CUQ_REPORTING_URL": "http://127.0.0.1:8090",
        # Not one of REQUIRED_VARS (ReportingSession.from_env doesn't read
        # it), but ServiceContainer() also builds a ProxySession, which does.
        "CUQ_PROXY_URL": "http://127.0.0.1:8080",
        "CUQ_PROXY_API_KEY": "cuq_op_test",
        "CUQ_PROXY_SECRET": "test-secret",
        "CUQ_PROXY_OPERATOR_ID": "cuq-999",
        "CUQ_PROXY_OPERATOR_NAME": "Test Operator",
    }
    values.update(overrides)
    for key, value in values.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


# ---------------------------------------------------------------------------
# ReportingSession.from_env
# ---------------------------------------------------------------------------


def test_from_env_builds_session_when_fully_configured(monkeypatch):
    _set_all(monkeypatch)
    session = ReportingSession.from_env()

    assert session.operator_id == "cuq-999"
    assert session.operator_name == "Test Operator"
    assert "test-secret" not in repr(session)  # never let the secret leak


def test_from_env_raises_naming_every_missing_var(monkeypatch):
    for var in REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ProxyConfigError) as exc_info:
        ReportingSession.from_env()

    message = str(exc_info.value)
    for var in REQUIRED_VARS:
        assert var in message


def test_from_env_raises_naming_only_the_one_missing_var(monkeypatch):
    _set_all(monkeypatch, CUQ_REPORTING_URL=None)

    with pytest.raises(ProxyConfigError) as exc_info:
        ReportingSession.from_env()

    message = str(exc_info.value)
    assert "CUQ_REPORTING_URL" in message
    for var in REQUIRED_VARS:
        if var != "CUQ_REPORTING_URL":
            assert var not in message


# ---------------------------------------------------------------------------
# ServiceContainer — reporting must be optional
# ---------------------------------------------------------------------------


def test_service_container_reporting_is_none_when_unconfigured(monkeypatch):
    _set_all(monkeypatch, CUQ_REPORTING_URL=None)

    container = ServiceContainer()

    assert container.reporting is None


def test_service_container_reporting_is_set_when_configured(monkeypatch):
    _set_all(monkeypatch)

    container = ServiceContainer()

    assert isinstance(container.reporting, ReportingSession)


@pytest.mark.asyncio
async def test_service_container_aclose_tolerates_missing_reporting(monkeypatch):
    _set_all(monkeypatch, CUQ_REPORTING_URL=None)
    container = ServiceContainer()
    assert container.reporting is None

    await container.aclose()  # must not raise despite reporting being None
