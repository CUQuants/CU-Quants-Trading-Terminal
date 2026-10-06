import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from exchange_services.service_container import ServiceContainer
from order_event_relay import OrderEventRelay
from news.service import NewsService
from routes.orders import router as orders_router
from routes.trades import router as trades_router
from routes.account import router as account_router
from routes.reporting import router as reporting_router
from routes.news import router as news_router

logging.basicConfig(level=logging.INFO)
# Some news APIs require credentials in query strings; omit HTTP request URLs.
logging.getLogger("httpx").setLevel(logging.WARNING)

"""
To run the backend:

uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    service_container = ServiceContainer()
    relay = OrderEventRelay(service_container)
    news_service = NewsService()

    app.state.service_container = service_container
    app.state.order_event_relay = relay
    app.state.news_service = news_service
    news_service.start()

    try:
        yield
    finally:
        await news_service.aclose()
        await relay.shutdown()
        await service_container.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders_router)
app.include_router(trades_router)
app.include_router(account_router)
app.include_router(reporting_router)
app.include_router(news_router)


@app.get("/")
async def health_check():
    return {"status": "ok"}
