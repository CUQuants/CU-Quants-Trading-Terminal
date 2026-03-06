import {
  createExchangeWsContext,
  type ExchangeWsAdapter,
  type ExchangeWsContextValue,
  type NormalizedUpdate,
} from "./createExchangeWsContext";
import type { OrderbookLevel } from "../types/orderbook";

/**
 * Gemini WebSocket API adapter for public market data.
 *
 * Docs: https://docs.gemini.com/websocket/fast-api/streams
 *
 * Streams used:
 *   {symbol}@depth20  – periodic L2 snapshot of top 20 levels (1 s cadence)
 *
 * Subscribe / unsubscribe follow the Gemini JSON‑RPC style:
 *   { "id": "…", "method": "subscribe",   "params": ["btcusd@depth20"] }
 *   { "id": "…", "method": "unsubscribe", "params": ["btcusd@depth20"] }
 */

// ── pair helpers ────────────────────────────────────────────────────────────

/** "BTC/USD" → "btcusd" */
function toGeminiSymbol(pair: string): string {
  const [base, quote] = pair.split("/");
  return `${base}${quote}`.toLowerCase();
}

/** "btcusd" → "BTC/USD" (assumes 3‑char quote; handles "usdt" as 4‑char) */
function fromGeminiSymbol(symbol: string): string {
  const s = symbol.toLowerCase();
  // Common quote currencies (longest first so "usdt" matches before "usd")
  const quotes = ["usdt", "usdc", "usd", "btc", "eth", "eur", "gbp", "sgd", "dai"];
  for (const q of quotes) {
    if (s.endsWith(q)) {
      const base = s.slice(0, s.length - q.length);
      return `${base.toUpperCase()}/${q.toUpperCase()}`;
    }
  }
  // Fallback: last 3 chars are quote
  return `${s.slice(0, -3).toUpperCase()}/${s.slice(-3).toUpperCase()}`;
}

// ── level parser ────────────────────────────────────────────────────────────

function parseLevels(raw: string[][]): OrderbookLevel[] {
  return raw.map(([price, qty]) => ({
    price: parseFloat(price),
    qty: parseFloat(qty),
  }));
}

// ── stream name constant ────────────────────────────────────────────────────

const STREAM_SUFFIX = "@depth20";

// ── adapter ─────────────────────────────────────────────────────────────────

const geminiAdapter: ExchangeWsAdapter = {
  name: "Gemini",
  wsUrl: "wss://ws.gemini.com",

  toWirePair: (pair) => toGeminiSymbol(pair),

  buildSubscribeMsg: (wirePairs) => ({
    id: "sub",
    method: "subscribe",
    params: wirePairs.map((wp) => `${wp}${STREAM_SUFFIX}`),
  }),

  buildUnsubscribeMsg: (wirePairs) => ({
    id: "unsub",
    method: "unsubscribe",
    params: wirePairs.map((wp) => `${wp}${STREAM_SUFFIX}`),
  }),

  parseMessage(raw): NormalizedUpdate | null {
    const msg = raw as Record<string, unknown>;

    // ── skip JSON‑RPC responses (subscribe confirmations, errors, etc.) ─────
    if ("id" in msg && ("status" in msg || "result" in msg || "error" in msg)) {
      return null;
    }

    // ── Format A: stream wrapper  { stream: "btcusd@depth20", data: {…} } ──
    if (typeof msg.stream === "string" && msg.data != null) {
      const streamName = msg.stream as string;
      const atIdx = streamName.indexOf("@");
      if (atIdx === -1) return null;

      const symbol = streamName.slice(0, atIdx);
      const pair = fromGeminiSymbol(symbol);
      const data = msg.data as {
        lastUpdateId?: number;
        bids: string[][];
        asks: string[][];
      };

      return {
        pair,
        type: "snapshot",
        bids: parseLevels(data.bids),
        asks: parseLevels(data.asks),
      };
    }

    // ── Format B: L2 differential depth update  { e:"depthUpdate", s:"btcusd", … }
    if (msg.e === "depthUpdate" && typeof msg.s === "string") {
      const pair = fromGeminiSymbol(msg.s as string);
      const bids = (msg.b as string[][] | undefined) ?? [];
      const asks = (msg.a as string[][] | undefined) ?? [];

      return {
        pair,
        type: "update",
        bids: parseLevels(bids),
        asks: parseLevels(asks),
      };
    }

    // ── Format C: raw partial depth snapshot (no stream wrapper) ────────────
    //    { lastUpdateId, bids, asks }
    //    We cannot determine the symbol so this only works for single‑symbol
    //    subscriptions.  Wrapped format (A) is the expected production path.
    if (
      "lastUpdateId" in msg &&
      Array.isArray(msg.bids) &&
      Array.isArray(msg.asks)
    ) {
      const rawSymbol =
        typeof msg.symbol === "string"
          ? msg.symbol
          : typeof msg.s === "string"
            ? msg.s
            : null;

      if (!rawSymbol) return null;

      return {
        pair: fromGeminiSymbol(rawSymbol),
        type: "snapshot",
        bids: parseLevels(msg.bids as string[][]),
        asks: parseLevels(msg.asks as string[][]),
      };
    }

    return null;
  },
};

// ── exports ─────────────────────────────────────────────────────────────────

const { Provider, useExchangeWs } = createExchangeWsContext(geminiAdapter);

export const GeminiWsProvider = Provider;
export const useGeminiWs = useExchangeWs;
export type GeminiWsContextValue = ExchangeWsContextValue;
