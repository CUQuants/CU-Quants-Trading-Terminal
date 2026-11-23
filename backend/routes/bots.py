"""Bot Monitor — the speedbyte bots on the Proxy box, the way xlrts's botmon sees them.

Every call is the gateway's `POST /v1/bots`, signed with the signed-in
trader's own credential: no SSH key, no shell on the box, and every start,
stop and save lands in the gateway's request_log under that trader's name.
What a trader may do is their `bot_role` on the gateway (viewer < operator <
editor); a refusal comes back as a 403 that says which role is needed.

Two things differ from xlrts, both on purpose:

* **Saves keep no backup.** `write_file` is sent `backup: false`, so the box
  no longer collects a `<file>.bak.<UTC>` per save. The save is still atomic,
  and is still refused if the file changed since it was opened.
* **New markets go into the CUQuants session.** `launch_market` and `start`
  are sent `placement: "window"`: a market with no tmux home gets a window
  named after it in `CUQuants` (after 0..4 comes CUQuants:5) instead of a
  session of its own.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from proxy_client.errors import ProxyError

from auth import current_container
from bot_templates import MARKET_PATTERN, LaunchRequest, config_yaml, subaccount_json
from exchange_services.service_container import ServiceContainer

router = APIRouter(prefix="/bots", tags=["bots"])

BOTS = "bots"
PLACEMENT = "window"

Kind = Literal["config", "subaccount"]


class SaveRequest(BaseModel):
    content: str = Field(max_length=256 * 1024)
    #: The sha256 `GET .../files/{kind}` returned — the version this edit started from.
    base_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


async def _call(container: ServiceContainer, action: str, payload: dict[str, Any]) -> Any:
    try:
        return await container.proxy.call(BOTS, action, payload)
    except ProxyError as exc:
        code = getattr(exc, "code", "")
        if code in ("AUTH_FAILED", "CREDENTIAL_EXPIRED"):
            raise  # app.proxy_error_handler ends the session
        raise HTTPException(status_code=_status(code), detail=_reason(exc)) from exc


def _status(code: str) -> int:
    return {
        "ACTION_NOT_PERMITTED": 403,  # no / too low a bot_role, or bots off on this gateway
        "MALFORMED_REQUEST": 400,
        "RATE_LIMITED": 429,
        "BOT_ERROR": 409,  # the box said no: already running, busy pane, stale edit...
    }.get(code, 502)


def _reason(exc: ProxyError) -> str:
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict) and detail.get("reason"):
        return str(detail["reason"])
    return str(exc)  # "CODE: message"


def _market(market: str) -> str:
    if not re.match(MARKET_PATTERN, market) or market == "sample":
        raise HTTPException(status_code=400, detail=f"invalid market name {market!r}")
    return market


@router.get("")
async def list_markets(container: ServiceContainer = Depends(current_container)) -> Any:
    """Every market with a config on the box: running?, where, last line of output."""
    return await _call(container, "list_markets", {})


@router.post("/launch")
async def launch_market(
    req: LaunchRequest, container: ServiceContainer = Depends(current_container)
) -> Any:
    """Create a market's config + subaccount (never overwriting either) and a
    CUQuants window for it with the venv active. Does not start the bot."""
    return await _call(container, "launch_market", {
        "market": req.market,
        "config": config_yaml(req),
        "subaccount": subaccount_json(req.market),
        "placement": PLACEMENT,
    })


@router.post("/{market}/start")
async def start(market: str, container: ServiceContainer = Depends(current_container)) -> Any:
    return await _call(container, "start", {"market": _market(market), "placement": PLACEMENT})


@router.post("/{market}/stop")
async def stop(market: str, container: ServiceContainer = Depends(current_container)) -> Any:
    return await _call(container, "stop", {"market": _market(market)})


@router.get("/{market}/files/{kind}")
async def read_file(
    market: str, kind: Kind, container: ServiceContainer = Depends(current_container)
) -> Any:
    return await _call(container, "read_file", {"market": _market(market), "kind": kind})


@router.post("/{market}/files/{kind}")
async def write_file(
    market: str,
    kind: Kind,
    req: SaveRequest,
    container: ServiceContainer = Depends(current_container),
) -> Any:
    return await _call(container, "write_file", {
        "market": _market(market),
        "kind": kind,
        "content": req.content,
        "base_sha256": req.base_sha256,
        "backup": False,
    })
