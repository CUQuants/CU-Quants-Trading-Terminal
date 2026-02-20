import os
import hmac
import hashlib
import base64
import json
from datetime import datetime, timezone
from typing import List

import httpx

from exchange_services.exchange import ExchangeService
from models import Order


class OkxService(ExchangeService):

    def __init__(self, base_url: str = "https://www.okx.com"):
        super().__init__(base_url)
        self.api_key = os.getenv("OKX_API_KEY", "")
        self.api_secret = os.getenv("OKX_API_SECRET", "")
        self.passphrase = os.getenv("OKX_API_PASSPHRASE", "")

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
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

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

    async def place_order(self, order: Order) -> Order:
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
            return order

    async def get_orders(self) -> List[Order]:
        request_path = "/api/v5/trade/orders-pending"
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
            orders.append(Order(
                symbol=self._from_native_pair(item["instId"]),
                exchange="okx",
                quantity=int(float(item["sz"])),
                price=float(item["px"]) if item.get("px") else None,
                side=item["side"],
                order_type="limit" if item["ordType"] == "limit" else "market",
            ))
        return orders

    async def cancel_order(self, order_id: str) -> bool:
        request_path = "/api/v5/trade/cancel-order"
        body_dict = {"ordId": order_id}
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
            return result.get("code") == "0"
