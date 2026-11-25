"""routes/orders.py GET: `pair` is optional — omitted means every open order
on the account (the dashboard's Open Orders panel), given means one pair."""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth import current_container
from models import OrderResponse
from routes.orders import router


def _order(oid, pair):
    return OrderResponse(id=oid, pair=pair, exchange="kraken", side="buy",
                         type="limit", price=1.0, size=2.0, status="open")


class FakeService:
    def __init__(self):
        self.calls = []

    async def get_orders(self, pair=None):
        self.calls.append(pair)
        orders = [_order("A", "BTC/USD"), _order("B", "ETH/USD")]
        return [o for o in orders if pair is None or o.pair == pair]


class FakeContainer:
    def __init__(self, service):
        self._service = service

    def get_service(self, exchange):
        return self._service


@pytest.fixture
def service():
    return FakeService()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_container] = lambda: FakeContainer(service)
    return TestClient(app)


def test_get_orders_without_pair_returns_all(client, service):
    r = client.get("/orders/kraken")
    assert r.status_code == 200
    assert [o["id"] for o in r.json()] == ["A", "B"]
    assert service.calls == [None]


def test_get_orders_with_pair_filters(client, service):
    r = client.get("/orders/kraken", params={"pair": "ETH/USD"})
    assert r.status_code == 200
    assert [o["id"] for o in r.json()] == ["B"]
    assert service.calls == ["ETH/USD"]
