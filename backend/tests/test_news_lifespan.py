"""Unit-test news startup/shutdown with isolated trading collaborators.

These tests load the real app wiring and NewsService. They do not test the
external trading SDK or replace its implementation for production imports.
"""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from news.providers import NewsProvider, ProviderResult
from news.service import NewsService


def load_app_with_trading_fakes(monkeypatch):
    events = []

    class FakeServiceContainer:
        async def aclose(self):
            events.append("container closed")

    class FakeOrderEventRelay:
        def __init__(self, container):
            self.container = container

        async def shutdown(self):
            events.append("relay closed")

    container_module = ModuleType("exchange_services.service_container")
    container_module.ServiceContainer = FakeServiceContainer
    relay_module = ModuleType("order_event_relay")
    relay_module.OrderEventRelay = FakeOrderEventRelay
    monkeypatch.setitem(sys.modules, container_module.__name__, container_module)
    monkeypatch.setitem(sys.modules, relay_module.__name__, relay_module)

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("news_lifespan_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, events


@pytest.mark.asyncio
@pytest.mark.parametrize("raise_in_lifespan", [False, True])
async def test_app_starts_news_and_closes_it_on_normal_or_exception_exit(
    monkeypatch, raise_in_lifespan,
):
    app_module, events = load_app_with_trading_fakes(monkeypatch)
    fetched = asyncio.Event()
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        fetched.set()
        return ProviderResult([{
            "source": "Example", "title": "Bitcoin startup update",
            "summary": "First refresh", "url": "https://example.test/startup",
        }])

    service = NewsService([NewsProvider("Example", fetch)], refresh_interval=0.01)
    monkeypatch.setattr(app_module, "NewsService", lambda: service)

    async def wait_for_refresh():
        while service.get_status().last_refresh is None:
            await asyncio.sleep(0)

    async def run_lifespan():
        async with app_module.lifespan(app_module.app):
            assert app_module.app.state.news_service is service
            await asyncio.wait_for(fetched.wait(), timeout=1)
            await asyncio.wait_for(wait_for_refresh(), timeout=1)
            assert service.get_status().next_refresh is not None
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app_module.app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/news")
                assert response.status_code == 200
                assert response.json()[0]["title"] == "Bitcoin startup update"
                response = await client.get("/news/status")
                assert response.status_code == 200
                assert response.json()["providers"][0]["state"] == "ok"
            if raise_in_lifespan:
                raise RuntimeError("Application body failed")

    if raise_in_lifespan:
        with pytest.raises(RuntimeError, match="Application body failed"):
            await run_lifespan()
    else:
        await run_lifespan()

    calls_at_close = calls
    await asyncio.sleep(0.02)
    assert calls == calls_at_close
    assert service.get_status().next_refresh is None
    assert events == ["relay closed", "container closed"]
