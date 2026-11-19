"""Sign in / out with a trader's own CU Quants gateway credential.

The four fields are exactly the `proxy:` values in a trader's xlrts
config.yaml: api_key, api_secret, operator_id, operator_name.

The secret is never sent anywhere: it is only the HMAC key the gateway
checks signatures with. It is held in this process's memory for the life of
the session (see `auth/sessions.py`) and never returned to the browser.

How a sign-in is checked, and what can and can't be checked:

* api_key / operator_id formats are checked here first (the gateway's own
  DB constraints, trading-gateway `migrations/002_schema.sql`), so a typo
  never reaches the gateway or counts against its shared failure budget.
* One signed `kraken` / `get_server_time` — exactly what xlrts does at
  startup. The gateway authenticates *before* forwarding, so any answer other
  than an auth error proves the key, the secret, and that operator_id owns
  that key.
* operator_name is only required to be non-blank by the gateway; it is
  recorded in the audit log as typed and can't be verified.
* The gateway answers a bad key, bad secret, wrong operator_id and a skewed
  clock with the same 401, so the error can't say which one was wrong.
"""

from __future__ import annotations

import logging
import math
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from proxy_client.errors import (
    AuthFailedError,
    CredentialExpiredError,
    ExchangeError,
    ProxyError,
    ProxyUnreachableError,
    RateLimitedError,
)

from auth import SESSION_COOKIE, UserSession, current_session
from auth.settings import AuthSettings
from exchange_services.proxy_session import ProxySession
from exchange_services.reporting_session import ReportingSession
from exchange_services.service_container import ServiceContainer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

API_KEY_RE = re.compile(r"^cuq_op_[A-Za-z0-9]{16,}$")
OPERATOR_ID_RE = re.compile(r"^cuq-[0-9]{3,5}$")
MAX_LEN = 256
MAX_NAME_LEN = 100


class LoginRequest(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    operator_id: str = ""
    operator_name: str = ""


class Operator(BaseModel):
    operator_id: str
    operator_name: str


def _fail(status: int, message: str, *, field: str | None = None,
          request_id: str = "", headers: dict | None = None) -> HTTPException:
    detail: dict = {"message": message}
    if field:
        detail["field"] = field
    if request_id:
        detail["request_id"] = request_id
    return HTTPException(status_code=status, detail=detail, headers=headers)


def _validate(body: LoginRequest) -> tuple[str, str, str, str]:
    api_key = body.api_key.strip()
    secret = body.api_secret.strip()
    operator_id = body.operator_id.strip()
    operator_name = " ".join(body.operator_name.split())  # collapse inner whitespace

    if not api_key:
        raise _fail(400, "API key is required.", field="api_key")
    if len(api_key) > MAX_LEN or not API_KEY_RE.match(api_key):
        raise _fail(400, "API key should look like cuq_op_ followed by letters and digits.", field="api_key")
    if not secret:
        raise _fail(400, "API secret is required.", field="api_secret")
    if len(secret) > MAX_LEN or any(c.isspace() for c in secret):
        raise _fail(400, "API secret contains spaces or is too long. Paste it exactly as issued.",
                    field="api_secret")
    if not operator_id:
        raise _fail(400, "Operator ID is required.", field="operator_id")
    if not OPERATOR_ID_RE.match(operator_id):
        raise _fail(400, "Operator ID should look like cuq-016.", field="operator_id")
    if not operator_name:
        raise _fail(400, "Operator name is required.", field="operator_name")
    if len(operator_name) > MAX_NAME_LEN or not operator_name.isprintable():
        raise _fail(400, f"Operator name must be at most {MAX_NAME_LEN} printable characters.",
                    field="operator_name")
    return api_key, secret, operator_id, operator_name


def _client_ip(request: Request) -> str:
    # With uvicorn --proxy-headers --forwarded-allow-ips 127.0.0.1 behind
    # Caddy this is the trader's address, not Caddy's.
    return request.client.host if request.client else "unknown"


def _set_cookie(response: Response, sid: str, settings: AuthSettings) -> None:
    response.set_cookie(
        SESSION_COOKIE, sid,
        max_age=int(settings.max_seconds),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def _clear_cookie(response: Response, settings: AuthSettings) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True,
        secure=settings.cookie_secure, samesite="strict",
    )


@router.post("/login", response_model=Operator)
async def login(body: LoginRequest, request: Request, response: Response) -> Operator:
    settings: AuthSettings = request.app.state.auth_settings
    throttle = request.app.state.login_throttle
    ip = _client_ip(request)

    wait = throttle.retry_after(ip)
    if wait > 0:
        seconds = math.ceil(wait)
        raise _fail(429, f"Too many failed sign-ins. Try again in {seconds} s.",
                    headers={"Retry-After": str(seconds)})

    api_key, secret, operator_id, operator_name = _validate(body)

    proxy = ProxySession(
        base_url=settings.proxy_url,
        api_key=api_key,
        secret=secret,
        operator_id=operator_id,
        operator_name=operator_name,
        ws_url=settings.proxy_ws_url,
    )
    try:
        await proxy.call("kraken", "get_server_time", {})
    except ExchangeError:
        # The gateway authenticated us and forwarded; Kraken itself erred.
        # The credential is good — sign in anyway.
        logger.warning("Sign-in check for %s reached Kraken, which erred; accepting", operator_id)
    except (AuthFailedError, CredentialExpiredError) as exc:
        await proxy.aclose()
        throttle.record_failure(ip)
        logger.info("Sign-in rejected for %s from %s: %s", operator_id, ip, exc.code)
        if isinstance(exc, CredentialExpiredError):
            raise _fail(401, "This credential has been revoked or has expired. Ask the club "
                             "liaison for a new one.", request_id=exc.request_id) from None
        raise _fail(401, "The gateway did not accept these credentials. Check the API key, "
                         "secret and operator ID (and that your computer's clock is right).",
                    request_id=exc.request_id) from None
    except RateLimitedError as exc:
        await proxy.aclose()
        raise _fail(429, "The gateway is rate-limiting sign-ins right now. Wait a minute and "
                         "try again.", request_id=exc.request_id,
                    headers={"Retry-After": str(math.ceil(exc.retry_after or 60))}) from None
    except ProxyUnreachableError as exc:
        await proxy.aclose()
        raise _fail(503, "Can't reach the trading gateway. Try again shortly.",
                    request_id=exc.request_id) from None
    except ProxyError as exc:
        await proxy.aclose()
        logger.warning("Sign-in check for %s failed: %s", operator_id, exc.code)
        raise _fail(502, f"The gateway refused the sign-in check ({exc.code}).",
                    request_id=exc.request_id) from None
    except BaseException:
        await proxy.aclose()
        raise

    throttle.record_success(ip)
    reporting = None
    if settings.reporting_url:
        reporting = ReportingSession(settings.reporting_url, api_key, secret, operator_id, operator_name)

    store = request.app.state.sessions
    # Signing in again from the same browser replaces that browser's session.
    await store.destroy(request.cookies.get(SESSION_COOKIE), reason="replaced")
    session = store.add(ServiceContainer(proxy, reporting), operator_id, operator_name)
    _set_cookie(response, session.session_id, settings)
    return Operator(operator_id=operator_id, operator_name=operator_name)


@router.get("/me", response_model=Operator)
async def me(session: UserSession = Depends(current_session)) -> Operator:
    return Operator(operator_id=session.operator_id, operator_name=session.operator_name)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> Response:
    await request.app.state.sessions.destroy(request.cookies.get(SESSION_COOKIE))
    response.status_code = 204
    _clear_cookie(response, request.app.state.auth_settings)
    return response
