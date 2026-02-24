import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from exchange_services.service_container import ServiceContainer
from order_event_relay import OrderEventRelay
from routes.orders import router as orders_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    service_container = ServiceContainer()
    relay = OrderEventRelay(service_container)

    app.state.service_container = service_container
    app.state.order_event_relay = relay

    yield

    await relay.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders_router)


@app.get("/")
async def health_check():
    return {"status": "ok"}
