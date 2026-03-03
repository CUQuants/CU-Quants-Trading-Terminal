import type { Exchange } from "../types/orderbook";
import type { AvailableCash, AvailablePosition } from "../types/account";
import { ApiError } from "./orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(body || `Request failed: ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function fetchAvailableCash(
  exchange: Exchange,
  pair: string,
): Promise<AvailableCash> {
  return request(
    `${API_BASE}/account/cash/${exchange}?pair=${encodeURIComponent(pair)}`,
  );
}

export function fetchAvailablePositions(
  exchange: Exchange,
  pair: string,
): Promise<AvailablePosition> {
  return request(
    `${API_BASE}/account/positions/${exchange}?pair=${encodeURIComponent(pair)}`,
  );
}
