import type { Exchange } from "../types/orderbook";
import type { Order, OrderParams, OrderResult } from "../types/orders";

import { ApiError, request } from "./client";

export function fetchOrders(exchange: Exchange, pair: string): Promise<Order[]> {
  return request(`/orders/${exchange}?pair=${encodeURIComponent(pair)}`);
}

export function placeOrder(exchange: Exchange, params: OrderParams): Promise<OrderResult> {
  return request(`/orders/${exchange}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export function cancelOrder(exchange: Exchange, orderId: string, pair: string): Promise<void> {
  return request(`/orders/${exchange}/${orderId}?pair=${encodeURIComponent(pair)}`, {
    method: "DELETE",
  });
}

export { ApiError };
