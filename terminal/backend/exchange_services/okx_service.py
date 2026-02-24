import os
import hmac
import hashlib
import base64
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from exchange_services.exchange import ExchangeService
from exchange_services.okx_order_stream import OkxOrderEventStream
from models import PlaceOrderRequest, OrderResponse


class OkxService(ExchangeService):

    def __init__(self, base_url: str = "https://us.okx.com", simulated: bool = False):
        super().__init__(base_url)
        self.api_key = os.getenv("OKX_API_KEY", "")
        self.api_secret = os.getenv("OKX_API_SECRET", "")
        self.passphrase = os.getenv("OKX_API_PASSPHRASE", "")
        self.simulated = simulated
        self._us = "us.okx.com" in base_url
        self._order_stream: OkxOrderEventStream | None = None

    # ------------------------------------------------------------------
    # Auth / signing (REST)
    # ------------------------------------------------------------------

    def _get_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        prehash = timestamp + method.upper() + request_path + body
        signature = hmac.new(
            self.api_secret.encode(),
            prehash.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode()

    def _get_headers(self, method: str, request_path: str, body: str = "") -> dict:
        timestamp = self._get_timestamp()
        sign = self._sign(timestamp, method, request_path, body)
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "x-simulated-trading": "1" if self.simulated else "0",
        }

    # ------------------------------------------------------------------
    # Pair normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _build_query_string(params: dict) -> str:
        parts = [f"{k}={v}" for k, v in params.items() if v is not None and v != ""]
        return "?" + "&".join(parts) if parts else ""

    def _to_native_pair(self, pair: str) -> str:
        """BTC/USD -> BTC-USDT"""
        base, quote = pair.split("/")
        if quote == "USD":
            quote = "USDT"
        return f"{base}-{quote}"

    def _from_native_pair(self, native_pair: str) -> str:
        """BTC-USDT -> BTC/USD"""
        base, quote = native_pair.split("-")
        if quote == "USDT":
            quote = "USD"
        return f"{base}/{quote}"

    # ------------------------------------------------------------------
    # REST: orders
    # ------------------------------------------------------------------

    async def place_order(self, request: PlaceOrderRequest) -> OrderResponse:
        request_path = "/api/v5/trade/order"
        body_dict = {
            "instId": self._to_native_pair(request.pair),
            "tdMode": "cash",
            "side": request.side,
            "ordType": request.type,
            "sz": str(request.size),
        }
        if request.type == "limit" and request.price is not None:
            body_dict["px"] = str(request.price)

        body = json.dumps(body_dict)
        headers = self._get_headers("POST", request_path, body)

        data = await self._request("POST", request_path, body=body, headers=headers)
        if data.get("code") != "0":
            raise Exception(f"OKX place_order failed: {data}")

        order_id = data["data"][0]["ordId"]
        return OrderResponse(
            id=order_id,
            pair=request.pair,
            exchange="okx",
            side=request.side,
            type=request.type,
            price=request.price,
            size=request.size,
            status="live",
        )

    async def get_orders(self, pair: Optional[str] = None) -> List[OrderResponse]:
        base_path = "/api/v5/trade/orders-pending"
        params: dict = {"instType": "SPOT"}
        if pair:
            params["instId"] = self._to_native_pair(pair)

        query = self._build_query_string(params)
        request_path = base_path + query
        headers = self._get_headers("GET", request_path)

        data = await self._request("GET", request_path, headers=headers)

        orders: List[OrderResponse] = []
        for item in data.get("data", []):
            orders.append(OrderResponse(
                id=item["ordId"],
                pair=self._from_native_pair(item["instId"]),
                exchange="okx",
                side=item["side"],
                type="limit" if item["ordType"] == "limit" else "market",
                price=float(item["px"]) if item.get("px") else None,
                size=float(item["sz"]),
                status=item["state"],
                created_at=item.get("cTime"),
            ))
        return orders

    async def cancel_order(self, order_id: str, pair: str) -> bool:
        request_path = "/api/v5/trade/cancel-order"
        body_dict = {
            "ordId": order_id,
            "instId": self._to_native_pair(pair),
        }
        body = json.dumps(body_dict)
        headers = self._get_headers("POST", request_path, body)

        result = await self._request("POST", request_path, body=body, headers=headers)
        return result.get("code") == "0"

    # ------------------------------------------------------------------
    # WS: order event stream
    # ------------------------------------------------------------------

    async def start_order_stream(self, event_queue: asyncio.Queue) -> None:
        if self._order_stream is not None:
            return
        self._order_stream = OkxOrderEventStream(
            api_key=self.api_key,
            api_secret=self.api_secret,
            passphrase=self.passphrase,
            simulated=self.simulated,
            us=self._us,
            pair_normalizer=self._from_native_pair,
        )
        await self._order_stream.start(event_queue)

    async def stop_order_stream(self) -> None:
        if self._order_stream:
            await self._order_stream.stop()
            self._order_stream = None
