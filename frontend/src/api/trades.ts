import type { Exchange } from "../types/orderbook";
import type { TradesPage } from "../types/trades";
import { apiFetch } from "./client";

/**
 * One page of fills for an exchange, newest first. Pass the returned
 * `next_offset` back as `offset` to get older fills; it is null when there
 * are no more (only Kraken pages today).
 */
export async function fetchTrades(
  exchange: Exchange,
  { pair, limit = 100, offset = 0 }: { pair?: string; limit?: number; offset?: number } = {},
): Promise<TradesPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (pair) params.set("pair", pair);
  if (offset) params.set("offset", String(offset));

  const res = await apiFetch(`/trades/${exchange}?${params}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `Request failed: ${res.status}`);
  }
  return res.json();
}
