from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request

from proxy_client.errors import ProxyError

router = APIRouter(prefix="/pnl", tags=["pnl"])


@router.get("")
async def get_pnl(request: Request, group_by: str = Query(default="pair")) -> Dict[str, Any]:
    """The club's PnL report from RMU Core, via the gateway's `POST /v1/rmu/pnl`.

    Returned unchanged (decimal values stay strings), so the terminal shows
    exactly the RMU's numbers.
    """
    proxy = request.app.state.service_container.proxy
    try:
        return await proxy.get_pnl(group_by=group_by)
    except ProxyError as exc:
        raise HTTPException(status_code=_status(exc), detail=_detail(exc)) from exc


def _status(exc: ProxyError) -> int:
    code = getattr(exc, "code", "")
    if code in ("AUTH_FAILED", "CREDENTIAL_EXPIRED"):
        return 401
    if code == "MALFORMED_REQUEST":
        return 400
    if code in ("PNL_UNAVAILABLE", "HTTP_404"):
        return 503
    if code == "RATE_LIMITED":
        return 429
    return 502


def _detail(exc: ProxyError) -> str:
    code = getattr(exc, "code", "") or "PROXY_ERROR"
    if code == "PNL_UNAVAILABLE" and getattr(exc, "http_status", None) == 404:
        return ("PNL_UNAVAILABLE: the gateway's PnL route isn't configured "
                "(RMU_URL / RMU_PNL_TOKEN unset, or the gateway predates the route).")
    if code == "PNL_UNAVAILABLE":
        return "PNL_UNAVAILABLE: the gateway couldn't get a report from the RMU. Retry shortly."
    if code == "HTTP_404":
        # A bare 404 with no Proxy error code: no such route on this gateway.
        return ("The gateway has no PnL route (POST /v1/rmu/pnl answered a bare 404). "
                "Deploy trading-gateway with the rmu-pnl-route change and restart it.")
    return str(exc)  # already "CODE: message"
