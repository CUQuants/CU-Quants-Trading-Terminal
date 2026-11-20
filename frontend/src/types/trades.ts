import type { Exchange } from "./orderbook";

export interface Trade {
  id: string;
  order_id: string;
  pair: string;
  exchange: Exchange;
  side: "buy" | "sell";
  // Exact decimal strings from the exchange (e.g. "95000.12340"). Never
  // round-trip these through Number for display; use formatExact.
  price: string;
  size: string;
  notional: string;
  fee: string;
  fee_currency: string;
  role: "maker" | "taker";
  timestamp: string;
}

export interface TradesPage {
  trades: Trade[];
  next_offset: number | null;
}
