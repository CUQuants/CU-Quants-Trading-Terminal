import type { Exchange } from "../types/orderbook";
import type { Trade } from "../types/trades";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchTrades(
  exchange: Exchange,
  pair?: string,
  limit: number = 100,
): Promise<Trade[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (pair) params.set("pair", pair);

  const res = await fetch(`${API_BASE}/trades/${exchange}?${params}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `Request failed: ${res.status}`);
  }
  return res.json();
}
