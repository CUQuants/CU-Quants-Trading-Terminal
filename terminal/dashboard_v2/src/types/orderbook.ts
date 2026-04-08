export type Exchange = "kraken" | "okx" | "gemini";

export interface OrderbookLevel {
  price: number;
  qty: number;
}

export interface OrderbookData {
  symbol: string;
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  checksum?: number;
}

// --- Kraken WebSocket types ---

export interface KrakenBookMessage {
  channel: "book";
  type: "snapshot" | "update";
  data: Array<{
    symbol: string;
    bids?: OrderbookLevel[];
    asks?: OrderbookLevel[];
    checksum?: number;
  }>;
}

export interface KrakenSubscribeMessage {
  method: "subscribe";
  params: {
    channel: "book";
    symbol: string[];
    depth: number;
    snapshot: boolean;
  };
}

export type KrakenMessage =
  | KrakenBookMessage
  | { channel: string;[key: string]: unknown };

// --- OKX WebSocket types ---

/** OKX sends price levels as string arrays: [price, size, liquidatedOrders, numOrders] */
export type OkxRawLevel = [string, string, string, string];

export interface OkxBookData {
  asks: OkxRawLevel[];
  bids: OkxRawLevel[];
  ts: string;
  checksum?: number;
}

export interface OkxBookMessage {
  arg: {
    channel: string;
    instId: string;
  };
  action: "snapshot" | "update";
  data: OkxBookData[];
}

/**
 * Exchanges that have a backend relay at localhost:8000
 * (order events WS, REST orders, account endpoints).
 */
export const BACKEND_EXCHANGES: ReadonlySet<Exchange> = new Set<Exchange>([
  "kraken",
  "okx",
  "gemini",
]);

/** Type-guard helper: returns true if the exchange has backend support. */
export function hasBackend(exchange: Exchange): boolean {
  return BACKEND_EXCHANGES.has(exchange);
}
