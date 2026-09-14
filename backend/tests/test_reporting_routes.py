"""Unit tests for routes/reporting.py — driven through a fake reporting
session and FastAPI's TestClient, the same "fake the one collaborator"
approach test_okx_service.py uses for ProxySession.

Only the logic that lives in this route module itself is worth testing here:
account.py/trades.py are dumb pass-throughs with no branching, but this
module owns two things nothing else does — the 503-when-unconfigured guard
and the ProxyError -> HTTP status mapping — plus /logs's 13-parameter
passthrough, where a typo'd kwarg would silently drop a filter instead of
raising.
"""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from proxy_client.errors import (
    ActionNotPermittedError,
    AuthFailedError,
    CredentialExpiredError,
    MalformedRequestError,
    ProxyError,
)

from routes.reporting import router


class FakeReporting:
    """Stands in for ReportingSession. Records the kwargs query_logs was
    called with, returns canned bodies (or raises a canned exception) keyed
    by method name."""

    def __init__(self):
        self.last_query_logs_kwargs = None
        self._responses = {}

    def set(self, name, response):
        self._responses[name] = response

    def _resolve(self, name, default):
        response = self._responses.get(name)
        if isinstance(response, Exception):
            raise response
        return response if response is not None else default

    async def log_health(self):
        return self._resolve("log_health", {
            "months_of_runway": 12, "default_partition_rows": 0,
            "unprotected_partitions": 0, "rows_last_24h": 0,
            "newest_row": None, "max_clock_skew_sec": None,
        })

    async def unresolved_orders(self):
        return self._resolve("unresolved_orders", [])

    async def auth_failures(self):
        return self._resolve("auth_failures", [])

    async def query_logs(self, **filters):
        self.last_query_logs_kwargs = filters
        return self._resolve("query_logs", {"logs": [], "next_cursor": None})


class FakeContainer:
    def __init__(self, reporting):
        self.reporting = reporting


def make_client(reporting) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.service_container = FakeContainer(reporting)
    return TestClient(app)


# ---------------------------------------------------------------------------
# 503 when the reporting API isn't configured for this deployment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [
    "/reporting/health", "/reporting/unresolved", "/reporting/auth-failures", "/reporting/logs",
])
def test_returns_503_when_reporting_not_configured(path):
    client = make_client(None)
    resp = client.get(path)

    assert resp.status_code == 503
    assert "CUQ_REPORTING_URL" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Happy path — one representative call per route
# ---------------------------------------------------------------------------


def test_health_returns_reporting_data():
    fake = FakeReporting()
    fake.set("log_health", {
        "months_of_runway": 6, "default_partition_rows": 3,
        "unprotected_partitions": 1, "rows_last_24h": 42,
        "newest_row": "2026-01-01 00:00:00+00:00", "max_clock_skew_sec": 0.1,
    })
    resp = make_client(fake).get("/reporting/health")

    assert resp.status_code == 200
    assert resp.json()["months_of_runway"] == 6


def test_unresolved_returns_list():
    fake = FakeReporting()
    fake.set("unresolved_orders", [{
        "request_id": "r1", "timestamp": "2026-01-01 00:00:00+00:00",
        "operator_id": "cuq-002", "operator_name": "Op", "system_name": None,
        "exchange": "okx", "action": "place_order", "source_ip": "127.0.0.1",
        "unresolved_for": "0:05:00",
    }])
    resp = make_client(fake).get("/reporting/unresolved")

    assert resp.status_code == 200
    assert resp.json()[0]["request_id"] == "r1"


def test_auth_failures_returns_list():
    fake = FakeReporting()
    fake.set("auth_failures", [{
        "api_key_id": "cuq_op_x", "source_ip": "127.0.0.1",
        "failures": 3, "latest": "2026-01-01 00:00:00+00:00",
    }])
    resp = make_client(fake).get("/reporting/auth-failures")

    assert resp.status_code == 200
    assert resp.json()[0]["failures"] == 3


def test_logs_returns_page():
    fake = FakeReporting()
    fake.set("query_logs", {"logs": [], "next_cursor": "abc"})
    resp = make_client(fake).get("/reporting/logs")

    assert resp.status_code == 200
    assert resp.json()["next_cursor"] == "abc"


# ---------------------------------------------------------------------------
# /logs filter passthrough — every kwarg reaches query_logs by name
# ---------------------------------------------------------------------------


def test_logs_forwards_every_filter_by_name():
    fake = FakeReporting()
    params = {
        "since": "2026-01-01T00:00:00",
        "until": "2026-01-02T00:00:00",
        "operator_id": "cuq-002",
        "operator_name": "Op",
        "exchange": "okx",
        "action": "place_order",
        "response_status": "error",
        "error_code": "EXCHANGE_ERROR",
        "api_key_id": "cuq_op_x",
        "source_ip": "127.0.0.1",
        "request_id": "abc-123",
        "limit": 10,
        "cursor": "opaque-cursor",
    }
    resp = make_client(fake).get("/reporting/logs", params=params)

    assert resp.status_code == 200
    assert fake.last_query_logs_kwargs == params


def test_logs_omits_unset_filters():
    fake = FakeReporting()
    make_client(fake).get("/reporting/logs")

    assert fake.last_query_logs_kwargs == {
        "since": None, "until": None, "operator_id": None, "operator_name": None,
        "exchange": None, "action": None, "response_status": None, "error_code": None,
        "api_key_id": None, "source_ip": None, "request_id": None, "limit": None,
        "cursor": None,
    }


# ---------------------------------------------------------------------------
# ProxyError -> HTTP status mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("exc,expected_status", [
    (AuthFailedError("bad creds"), 401),
    (CredentialExpiredError("expired"), 401),
    (ActionNotPermittedError("not an auditor"), 403),
    (MalformedRequestError("bad cursor"), 400),
    (ProxyError("boom", code="PROXY_UNREACHABLE"), 502),  # unrecognized -> fallback
])
def test_reporting_errors_map_to_the_right_http_status(exc, expected_status):
    fake = FakeReporting()
    fake.set("log_health", exc)
    resp = make_client(fake).get("/reporting/health")

    assert resp.status_code == expected_status
