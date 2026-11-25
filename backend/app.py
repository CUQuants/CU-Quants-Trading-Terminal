import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from proxy_client.errors import ProxyError

from auth import SESSION_COOKIE, AuthSettings, LoginThrottle, SessionStore, origin_allowed
from routes.auth import router as auth_router
from routes.orders import router as orders_router
from routes.trades import router as trades_router
from routes.account import router as account_router
from routes.reporting import router as reporting_router
from routes.pnl import router as pnl_router
from routes.risk import router as risk_router
from routes.bots import router as bots_router

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
To run the backend:

uv run uvicorn app:app --reload --host 127.0.0.1 --port 8000

Traders sign in from the browser (POST /auth/login) with their own gateway
credential; the server's env only says where the gateway is (CUQ_PROXY_URL).
Run a single worker: signed-in sessions live in this process's memory.
"""

def create_app(settings: AuthSettings | None = None) -> FastAPI:
    settings = settings or AuthSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = SessionStore(idle_seconds=settings.idle_seconds, max_seconds=settings.max_seconds)
        app.state.sessions = store
        app.state.login_throttle = LoginThrottle()
        sweeper = asyncio.create_task(store.run_sweeper())

        yield

        sweeper.cancel()
        try:
            await sweeper
        except asyncio.CancelledError:
            pass
        await store.close_all()

    app = FastAPI(lifespan=lifespan)
    app.state.auth_settings = settings

    # Production (Caddy) and local dev (the Vite proxy) are both same-origin,
    # so no CORS is needed. Only an explicitly listed extra origin gets it.
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=sorted(settings.allowed_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type"],
        )

    @app.middleware("http")
    async def reject_cross_site_writes(request: Request, call_next):
        """Defence in depth on top of SameSite=Strict: a state-changing
        request (including /auth/login) from another site's page is refused
        outright."""
        if request.method in _UNSAFE_METHODS and not origin_allowed(request):
            return JSONResponse(status_code=403, content={"detail": "Cross-site request refused."})
        return await call_next(request)

    app.add_exception_handler(ProxyError, proxy_error_handler)

    app.include_router(auth_router)
    app.include_router(orders_router)
    app.include_router(trades_router)
    app.include_router(account_router)
    app.include_router(reporting_router)
    app.include_router(pnl_router)
    app.include_router(risk_router)
    app.include_router(bots_router)

    @app.get("/")
    async def health_check():
        return {"status": "ok"}

    return app


_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Gateway error codes that mean "this trader's credential no longer works".
_CREDENTIAL_DEAD = {"AUTH_FAILED", "CREDENTIAL_EXPIRED"}
_STATUS_BY_CODE = {
    "AUTH_FAILED": 401,
    "CREDENTIAL_EXPIRED": 401,
    "ACTION_NOT_PERMITTED": 403,
    "MALFORMED_REQUEST": 400,
    "RATE_LIMITED": 429,
}


async def proxy_error_handler(request: Request, exc: ProxyError):
    """A gateway error that a route didn't handle itself. Anything not mapped
    stays a 5xx, which the order panel already reads as "outcome unknown".

    If the gateway says the credential is dead (revoked mid-session), the
    trader's session is ended too, so the browser drops back to sign-in.
    """
    code = getattr(exc, "code", "") or "PROXY_ERROR"
    if code in _CREDENTIAL_DEAD:
        await request.app.state.sessions.destroy(request.cookies.get(SESSION_COOKIE),
                                                 reason=f"gateway {code}")
    status = _STATUS_BY_CODE.get(code, 502)
    content = {"detail": str(exc)}
    if getattr(exc, "request_id", ""):
        content["request_id"] = exc.request_id
    return JSONResponse(status_code=status, content=content)


# Built at import so a missing CUQ_PROXY_URL fails the boot, not the first login.
app = create_app()
