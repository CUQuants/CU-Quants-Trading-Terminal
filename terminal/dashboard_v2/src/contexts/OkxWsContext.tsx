import {
  createExchangeWsContext,
  type ExchangeWsAdapter,
  type ExchangeWsContextValue,
  type NormalizedMessage,
} from "./createExchangeWsContext";
import type { OkxBookMessage, OkxRawLevel } from "../types/orderbook";
import type { OrderbookLevel } from "../types/orderbook";

function toNativePair(pair: string): string {
  const [base, quote] = pair.split("/").map((s) => s.trim().toUpperCase());
  const okxQuote = quote === "USD" || quote === "USDT" ? "USDT" : quote;
  return `${base}-${okxQuote}`;
}

function fromNativePair(native: string): string {
  const [base, quote] = native.split("-");
  return `${base}/${quote === "USDT" ? "USD" : quote}`;
}

function parseOkxLevels(raw: OkxRawLevel[]): OrderbookLevel[] {
  return raw.map(([price, qty]) => ({
    price: parseFloat(price),
    qty: parseFloat(qty),
  }));
}

const okxAdapter: ExchangeWsAdapter = {
  name: "Okx",
  wsUrl: "wss://wsus.okx.com:8443/ws/v5/public",

  toWirePair: (pair) => toNativePair(pair),

  buildSubscribeMsg: (wirePairs) => ({
    op: "subscribe",
    args: wirePairs.map((instId) => ({ channel: "books", instId })),
  }),

  buildUnsubscribeMsg: (wirePairs) => ({
    op: "unsubscribe",
    args: wirePairs.map((instId) => ({ channel: "books", instId })),
  }),

  parseMessage(raw): NormalizedMessage | null {
    const msg = raw as Record<string, unknown>;

    // Control / error frames
    if ("event" in msg) {
      const event = msg.event as string | undefined;
      if (event !== "error") return null;

      const arg = msg.arg as { instId?: string } | undefined;
      let pair: string | undefined;
      if (arg?.instId) {
        try {
          pair = fromNativePair(arg.instId);
        } catch {
          pair = undefined;
        }
      }

      const code = (msg.code as string | undefined) ?? undefined;
      const rawMessage = (msg.msg as string | undefined) ?? "OKX WebSocket error";
      const message =
        code != null && code !== ""
          ? `OKX: ${rawMessage} (code ${code})`
          : `OKX: ${rawMessage}`;

      return {
        type: "error",
        scope: pair ? "pair" : "connection",
        pair,
        code,
        message,
        raw: msg,
      };
    }

    const bookMsg = msg as unknown as OkxBookMessage;
    if (!bookMsg.data || !bookMsg.action) return null;

    const d = bookMsg.data[0];
    const pair = fromNativePair(bookMsg.arg.instId);

    return {
      pair,
      instId: bookMsg.arg.instId,
      type: bookMsg.action,
      bids: parseOkxLevels(d.bids),
      asks: parseOkxLevels(d.asks),
      checksum: d.checksum,
    };
  },
};

const { Provider, useExchangeWs } = createExchangeWsContext(okxAdapter);

export const OkxWsProvider = Provider;
export const useOkxWs = useExchangeWs;
export type OkxWsContextValue = ExchangeWsContextValue;
