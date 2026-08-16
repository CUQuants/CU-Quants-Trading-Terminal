import type { Exchange } from "../types/orderbook";
import type { Order, OrderParams, OrderResult } from "../types/orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(body || `Request failed: ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function fetchOrders(exchange: Exchange, pair: string): Promise<Order[]> {
  return request(`${API_BASE}/orders/${exchange}?pair=${encodeURIComponent(pair)}`);
}

export function placeOrder(exchange: Exchange, params: OrderParams): Promise<OrderResult> {
  return request(`${API_BASE}/orders/${exchange}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export function cancelOrder(exchange: Exchange, orderId: string, pair: string): Promise<void> {
  return request(`${API_BASE}/orders/${exchange}/${orderId}?pair=${encodeURIComponent(pair)}`, {
    method: "DELETE",
  });
}

export { ApiError };
