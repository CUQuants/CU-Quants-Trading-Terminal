"""OkxOrderEventStream against an in-process fake Proxy speaking the OKX
WS dialect.

Proves the glue: signed handshake -> subscribe to the private `orders`
channel -> an OKX order frame relayed verbatim gets normalized onto the
queue in the shape the frontend already consumes, and connection
transitions surface as status events.
"""

import asyncio
import contextlib
import json
import os
import sys

import pytest
import websockets

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from exchange_services.okx_order_stream import OkxOrderEventStream


class FakeProxySession:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.api_key = "cuq_op_test"
        self.secret = "s3cr3t"
        self.operator_id = "cuq-014"
        self.operator_name = "J. Rivera"
        self.ws_url_override = ""


@contextlib.asynccontextmanager
async def _fake_gateway(handler):
    server = await websockets.serve(handler, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.close()
        await server.wait_closed()


async def _accept_auth(ws):
    await ws.recv()
    await ws.send(json.dumps({"event": "auth", "code": "0", "operator_id": "cuq-014"}))


@pytest.mark.asyncio
async def test_order_frame_normalized_onto_queue_and_status_emitted():
    async def handler(ws):
        await _accept_auth(ws)
        sub = json.loads(await ws.recv())
        assert sub == {
            "op": "subscribe",
            "args": [{"channel": "orders", "instType": "SPOT"}],
            "id": "1",
        }
        await ws.send(json.dumps({"event": "subscribe", "arg": sub["args"][0], "id": "1"}))
        # OKX private `orders` push, relayed verbatim
        await ws.send(json.dumps({
            "arg": {"channel": "orders", "instType": "SPOT"},
            "data": [{
                "instId": "BTC-USDT", "ordId": "OKX-42", "state": "filled",
                "side": "buy", "fillPx": "95000.1", "sz": "0.01", "uTime": "1730000000000",
            }],
        }))
        await ws.wait_closed()

    async with _fake_gateway(handler) as base_url:
        proxy = FakeProxySession(base_url)
        queue: asyncio.Queue = asyncio.Queue()
        stream = OkxOrderEventStream(
            proxy=proxy,
            pair_normalizer=lambda n: n.replace("-USDT", "/USD"),
        )
        await stream.start(queue)
        try:
            events = []
            deadline = asyncio.get_event_loop().time() + 5
            while asyncio.get_event_loop().time() < deadline:
                ev = await asyncio.wait_for(queue.get(), timeout=5)
                events.append(ev)
                if ev.get("type") == "order_event":
                    break
        finally:
            await stream.stop()

    assert {"type": "status", "exchange": "okx", "connectionStatus": "connected"} in events
    order_events = [e for e in events if e.get("type") == "order_event"]
    assert order_events == [{
        "type": "order_event",
        "exchange": "okx",
        "pair": "BTC/USD",
        "orderId": "OKX-42",
        "status": "filled",
        "side": "buy",
        "price": 95000.1,
        "size": 0.01,
        "timestamp": "1730000000000",
    }]


@pytest.mark.asyncio
async def test_unknown_order_state_is_dropped():
    async def handler(ws):
        await _accept_auth(ws)
        sub = json.loads(await ws.recv())
        await ws.send(json.dumps({"event": "subscribe", "arg": sub["args"][0], "id": "1"}))
        await ws.send(json.dumps({
            "arg": {"channel": "orders", "instType": "SPOT"},
            "data": [{"instId": "BTC-USDT", "ordId": "X", "state": "pending_cancel"}],
        }))
        await ws.wait_closed()

    async with _fake_gateway(handler) as base_url:
        queue: asyncio.Queue = asyncio.Queue()
        stream = OkxOrderEventStream(proxy=FakeProxySession(base_url))
        await stream.start(queue)
        try:
            # first event is the 'connected' status; no order_event should follow
            first = await asyncio.wait_for(queue.get(), timeout=5)
            assert first["connectionStatus"] == "connected"
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue.get(), timeout=0.5)
        finally:
            await stream.stop()
