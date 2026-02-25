import {
  createExchangeWsContext,
  type ExchangeWsAdapter,
  type ExchangeWsContextValue,
  type NormalizedUpdate,
} from "./createExchangeWsContext";
import type { KrakenMessage, KrakenBookMessage } from "../types/orderbook";

const DEPTH = 25;

const krakenAdapter: ExchangeWsAdapter = {
  name: "Kraken",
  wsUrl: "wss://ws.kraken.com/v2",

  toWirePair: (pair) => pair,

  buildSubscribeMsg: (wirePairs) => ({
    method: "subscribe",
    params: { channel: "book", symbol: wirePairs, depth: DEPTH, snapshot: true },
  }),

  buildUnsubscribeMsg: (wirePairs) => ({
    method: "unsubscribe",
    params: { channel: "book", symbol: wirePairs, depth: DEPTH },
  }),

  parseMessage(raw): NormalizedUpdate | null {
    const msg = raw as KrakenMessage;
    if (msg.channel !== "book") return null;

    const bookMsg = msg as KrakenBookMessage;
    const d = bookMsg.data[0];

    return {
      pair: d.symbol,
      type: bookMsg.type,
      bids: d.bids ?? [],
      asks: d.asks ?? [],
      checksum: d.checksum,
    };
  },
};

const { Provider, useExchangeWs } = createExchangeWsContext(krakenAdapter);

export const KrakenWsProvider = Provider;
export const useKrakenWs = useExchangeWs;
export type KrakenWsContextValue = ExchangeWsContextValue;
