from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from proxy_client.errors import ProxyError

from auth import current_container
from exchange_services.service_container import ServiceContainer

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("")
async def get_risk_status(
    container: ServiceContainer = Depends(current_container),
) -> Dict[str, Any]:
    """RMU Core's risk status, via the gateway's `POST /v1/rmu/risk`:
    `{"kill_switch": {...}}`, returned unchanged (decimals stay strings).

    Read-only. Clearing a trip is not served here yet.
    """
    try:
        return await container.proxy.get_risk_status()
    except ProxyError as exc:
        raise HTTPException(status_code=_status(exc), detail=_detail(exc)) from exc


def _status(exc: ProxyError) -> int:
    code = getattr(exc, "code", "")
    if code in ("AUTH_FAILED", "CREDENTIAL_EXPIRED"):
        return 401
    if code in ("RISK_STATUS_UNAVAILABLE", "HTTP_404"):
        return 503
    if code == "RATE_LIMITED":
        return 429
    return 502


def _detail(exc: ProxyError) -> str:
    code = getattr(exc, "code", "") or "PROXY_ERROR"
    if code == "RISK_STATUS_UNAVAILABLE" and getattr(exc, "http_status", None) == 404:
        return ("RISK_STATUS_UNAVAILABLE: the gateway's risk status route isn't configured "
                "(RMU_URL / RMU_PNL_TOKEN unset).")
    if code == "RISK_STATUS_UNAVAILABLE":
        return ("RISK_STATUS_UNAVAILABLE: the gateway couldn't get the kill switch status from the RMU. "
                "Retry shortly; if it persists, the RMU may predate the PnL token reading /v1/kill-switch.")
    if code == "HTTP_404":
        return ("The gateway has no risk status route (POST /v1/rmu/risk answered a bare 404). "
                "Deploy trading-gateway with the rmu-risk-status-route change and restart it.")
    return str(exc)  # already "CODE: message"
