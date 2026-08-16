import type { Exchange } from "./orderbook";

export interface Trade {
  id: string;
  order_id: string;
  pair: string;
  exchange: Exchange;
  side: "buy" | "sell";
  price: number;
  size: number;
  fee: number;
  fee_currency: string;
  role: "maker" | "taker";
  timestamp: string;
}
