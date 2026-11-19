"""ReportingSession and its optional wiring into ServiceContainer.

Reporting is optional: a deployment without CUQ_REPORTING_URL builds no
ReportingSession at sign-in, and the container must work without one.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.proxy_session import ProxySession
from exchange_services.reporting_session import ReportingSession
from exchange_services.service_container import ServiceContainer

CREDS = ("cuq_op_test", "test-secret", "cuq-999", "Test Operator")


def _proxy() -> ProxySession:
    return ProxySession("http://127.0.0.1:8080", *CREDS)


def test_reporting_session_never_leaks_the_secret():
    session = ReportingSession("http://127.0.0.1:8090", *CREDS)

    assert session.operator_id == "cuq-999"
    assert session.operator_name == "Test Operator"
    assert "test-secret" not in repr(session)


def test_proxy_session_never_leaks_the_secret():
    assert "test-secret" not in repr(_proxy())


def test_service_container_reporting_defaults_to_none():
    assert ServiceContainer(_proxy()).reporting is None


def test_service_container_keeps_the_given_reporting_session():
    reporting = ReportingSession("http://127.0.0.1:8090", *CREDS)
    assert ServiceContainer(_proxy(), reporting).reporting is reporting


@pytest.mark.asyncio
async def test_service_container_aclose_tolerates_missing_reporting():
    container = ServiceContainer(_proxy())
    await container.aclose()  # must not raise despite reporting being None
