import os
import hmac
import hashlib
import base64
import json
from datetime import datetime, timezone
from typing import List

import httpx

from dotenv import load_dotenv
load_dotenv()

from exchange_services.exchange import ExchangeService
from models import Order, OrderResponse


class OkxService(ExchangeService):

    def __init__(self, base_url: str = "https://us.okx.com", simulated: bool = False):
        super().__init__(base_url)
        self.api_key = os.getenv("OKX_API_KEY", "")
        self.api_secret = os.getenv("OKX_API_SECRET", "")
        self.passphrase = os.getenv("OKX_API_PASSPHRASE", "")
        self.simulated = simulated


    def _get_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        prehash = timestamp + method.upper() + request_path + body
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def _get_headers(self, method: str, request_path: str, body: str = "") -> dict:
        timestamp = self._get_timestamp()
        sign = self._sign(timestamp, method, request_path, body)
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "x-simulated-trading": "1" if self.simulated else "0",
        }
        return headers

    @staticmethod
    def _build_query_string(params: dict) -> str:
        parts = [f"{k}={v}" for k, v in params.items() if v is not None and v != ""]
        return "?" + "&".join(parts) if parts else ""

    def _to_native_pair(self, pair: str) -> str:
        """Convert normalized 'BTC/USD' format to OKX native 'BTC-USDT' format."""
        base, quote = pair.split("/")
        if quote == "USD":
            quote = "USDT"
        return f"{base}-{quote}"

    def _from_native_pair(self, native_pair: str) -> str:
        """Convert OKX native 'BTC-USDT' format to normalized 'BTC/USD' format."""
        base, quote = native_pair.split("-")
        if quote == "USDT":
            quote = "USD"
        return f"{base}/{quote}"

    async def place_order(self, order: Order) -> OrderResponse:
        request_path = "/api/v5/trade/order"
        body_dict = {
            "instId": self._to_native_pair(order.symbol),
            "tdMode": "cash",
            "side": order.side,
            "ordType": order.order_type,
            "sz": str(order.quantity),
        }
        if order.order_type == "limit" and order.price is not None:
            body_dict["px"] = str(order.price)

        body = json.dumps(body_dict)
        headers = self._get_headers("POST", request_path, body)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{request_path}",
                headers=headers,
                content=body,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") != "0":
                raise Exception(f"OKX place_order failed: {data}")

            order_id = data["data"][0]["ordId"]
            return OrderResponse(
                id=order_id,
                symbol=order.symbol,
                exchange=order.exchange,
                quantity=order.quantity,
                price=order.price,
                side=order.side,
                order_type=order.order_type,
                status="live",
            )

    async def get_orders(self, inst_type: str = "SPOT") -> List[Order]:
        base_path = "/api/v5/trade/orders-pending"
        query = self._build_query_string({"instType": inst_type})
        request_path = base_path + query
        headers = self._get_headers("GET", request_path)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{request_path}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        orders: List[Order] = []
        for item in data.get("data", []):
            orders.append(OrderResponse(
                symbol=self._from_native_pair(item["instId"]),
                exchange="okx",
                quantity=int(float(item["sz"])),
                price=float(item["px"]) if item.get("px") else None,
                side=item["side"],
                order_type="limit" if item["ordType"] == "limit" else "market",
                id=item["ordId"],
                status=item["state"],
            ))
        return orders

    async def cancel_order(self, order_id: str, inst_id: str) -> bool:
        request_path = "/api/v5/trade/cancel-order"
        body_dict = {"ordId": order_id, "instId": self._to_native_pair(inst_id)}
        body = json.dumps(body_dict)
        headers = self._get_headers("POST", request_path, body)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{request_path}",
                headers=headers,
                content=body,
            )
            response.raise_for_status()
            result = response.json()
            print(result)
            return result.get("code") == "0"
