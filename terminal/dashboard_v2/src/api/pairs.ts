import type { Exchange } from "../types/orderbook";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type ExchangePairsResponse = Partial<Record<Exchange, string[]>>;

export async function fetchExchangePairs(): Promise<ExchangePairsResponse> {
  const res = await fetch(`${API_BASE}/pairs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch exchange pairs: ${res.status}`);
  }

  return (await res.json()) as ExchangePairsResponse;
}
