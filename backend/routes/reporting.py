from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from proxy_client.errors import ProxyError
from models import (
    AuthFailureResponse,
    LogHealthResponse,
    LogPageResponse,
    UnresolvedOrderResponse,
)

router = APIRouter(prefix="/reporting", tags=["reporting"])

# proxy_admin.reporting only ever raises this subset (see
# proxy_client.reporting's module docstring) — anything else (e.g. a
# transport-level ProxyUnreachableError) falls back to 502.
_STATUS_BY_CODE = {
    "AUTH_FAILED": 401,
    "CREDENTIAL_EXPIRED": 401,
    "ACTION_NOT_PERMITTED": 403,
    "MALFORMED_REQUEST": 400,
}


def _reporting(request: Request):
    reporting = request.app.state.service_container.reporting
    if reporting is None:
        raise HTTPException(
            status_code=503,
            detail="Reporting API not configured on this deployment — set CUQ_REPORTING_URL.",
        )
    return reporting


def _reraise_as_http(exc: ProxyError):
    raise HTTPException(status_code=_STATUS_BY_CODE.get(exc.code, 502), detail=str(exc)) from exc


@router.get("/health", response_model=LogHealthResponse)
async def get_log_health(request: Request):
    """Partition runway, clock skew, default-partition drift."""
    reporting = _reporting(request)
    try:
        return await reporting.log_health()
    except ProxyError as e:
        _reraise_as_http(e)


@router.get("/unresolved", response_model=List[UnresolvedOrderResponse])
async def get_unresolved_orders(request: Request):
    """Orders forwarded to an exchange whose outcome was never recorded."""
    reporting = _reporting(request)
    try:
        return await reporting.unresolved_orders()
    except ProxyError as e:
        _reraise_as_http(e)


@router.get("/auth-failures", response_model=List[AuthFailureResponse])
async def get_auth_failures(request: Request):
    """Authentication failures in the last 7 days, by key and origin."""
    reporting = _reporting(request)
    try:
        return await reporting.auth_failures()
    except ProxyError as e:
        _reraise_as_http(e)


@router.get("/logs", response_model=LogPageResponse)
async def get_logs(
    request: Request,
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    operator_id: Optional[str] = Query(default=None),
    operator_name: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    response_status: Optional[str] = Query(default=None),
    error_code: Optional[str] = Query(default=None),
    api_key_id: Optional[str] = Query(default=None),
    source_ip: Optional[str] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1, le=200),
    cursor: Optional[str] = Query(default=None),
):
    """Filtered, paginated browse over request_log."""
    reporting = _reporting(request)
    try:
        return await reporting.query_logs(
            since=since,
            until=until,
            operator_id=operator_id,
            operator_name=operator_name,
            exchange=exchange,
            action=action,
            response_status=response_status,
            error_code=error_code,
            api_key_id=api_key_id,
            source_ip=source_ip,
            request_id=request_id,
            limit=limit,
            cursor=cursor,
        )
    except ProxyError as e:
        _reraise_as_http(e)
