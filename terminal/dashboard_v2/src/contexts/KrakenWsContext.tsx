import {
  createContext,
  useContext,
  useRef,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import type {
  OrderbookData,
  OrderbookLevel,
  KrakenMessage,
  KrakenBookMessage,
} from "../types/orderbook";

const KRAKEN_WS_URL = "wss://ws.kraken.com/v2";
const DEPTH = 25;
const FLUSH_INTERVAL_MS = 500;
const MAX_RETRIES = 3;
const BACKOFF_MS = [1000, 2000, 4000];

type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "failed";

export interface KrakenWsContextValue {
  connectionStatus: ConnectionStatus;
  lastUpdated: Date | null;
  orderbook: Record<string, OrderbookData>;
  subscribe: (pair: string) => void;
  unsubscribe: (pair: string) => void;
  subscribedPairs: string[];
}

const KrakenWsContext = createContext<KrakenWsContextValue | null>(null);

function applyLevelUpdate(
  current: OrderbookLevel[],
  updates: OrderbookLevel[],
  isBids: boolean,
): OrderbookLevel[] {
  const map = new Map<number, number>();
  for (const l of current) map.set(l.price, l.qty);
  for (const u of updates) {
    if (u.qty === 0) map.delete(u.price);
    else map.set(u.price, u.qty);
  }
  return Array.from(map.entries())
    .map(([price, qty]) => ({ price, qty }))
    .sort((a, b) => (isBids ? b.price - a.price : a.price - b.price))
    .slice(0, DEPTH);
}

export function KrakenWsProvider({ children }: { children: ReactNode }) {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [orderbooks, setOrderbooks] = useState<Record<string, OrderbookData>>(
    {},
  );
  const [subscribedPairs, setSubscribedPairs] = useState<string[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const booksRef = useRef<Record<string, OrderbookData>>({});
  const dirtyRef = useRef(false);
  const pairsRef = useRef<Set<string>>(new Set());
  const retriesRef = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectWs = useCallback(() => {
    if (pairsRef.current.size === 0) return;
    const ws = wsRef.current;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    setConnectionStatus("connecting");
    const socket = new WebSocket(KRAKEN_WS_URL);
    wsRef.current = socket;

    socket.onopen = () => {
      if (wsRef.current !== socket) return;
      setConnectionStatus("connected");
      retriesRef.current = 0;

      const symbols = [...pairsRef.current];
      if (symbols.length > 0) {
        socket.send(
          JSON.stringify({
            method: "subscribe",
            params: { channel: "book", symbol: symbols, depth: DEPTH, snapshot: true },
          }),
        );
      }
    };

    socket.onmessage = (ev: MessageEvent) => {
      if (wsRef.current !== socket) return;
      try {
        const message: KrakenMessage = JSON.parse(ev.data as string);
        if (message.channel !== "book") return;

        const bookMsg = message as KrakenBookMessage;
        const d = bookMsg.data[0];
        const pair = d.symbol;

        if (!pairsRef.current.has(pair)) return;

        if (bookMsg.type === "snapshot") {
          booksRef.current[pair] = {
            symbol: pair,
            bids: (d.bids ?? []).slice(0, DEPTH),
            asks: (d.asks ?? []).slice(0, DEPTH),
            checksum: d.checksum,
          };
          dirtyRef.current = true;
        } else if (bookMsg.type === "update" && booksRef.current[pair]) {
          const cur = booksRef.current[pair];
          booksRef.current[pair] = {
            ...cur,
            bids: d.bids
              ? applyLevelUpdate(cur.bids, d.bids, true)
              : cur.bids,
            asks: d.asks
              ? applyLevelUpdate(cur.asks, d.asks, false)
              : cur.asks,
            checksum: d.checksum,
          };
          dirtyRef.current = true;
        }
      } catch {
        /* malformed — skip */
      }
    };

    socket.onerror = () => {};

    socket.onclose = () => {
      if (wsRef.current !== socket) return;
      wsRef.current = null;

      if (pairsRef.current.size === 0) {
        setConnectionStatus("disconnected");
        return;
      }

      retriesRef.current += 1;
      if (retriesRef.current > MAX_RETRIES) {
        setConnectionStatus("failed");
        return;
      }
      setConnectionStatus("reconnecting");
      const delay =
        BACKOFF_MS[Math.min(retriesRef.current - 1, BACKOFF_MS.length - 1)];
      reconnectTimer.current = setTimeout(() => connectWs(), delay);
    };
  }, []);

  // Batched flush
  useEffect(() => {
    const id = setInterval(() => {
      if (dirtyRef.current) {
        setOrderbooks({ ...booksRef.current });
        setLastUpdated(new Date());
        dirtyRef.current = false;
      }
    }, FLUSH_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  const subscribe = useCallback(
    (pair: string) => {
      if (pairsRef.current.has(pair)) return;
      pairsRef.current.add(pair);
      setSubscribedPairs([...pairsRef.current]);

      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            method: "subscribe",
            params: { channel: "book", symbol: [pair], depth: DEPTH, snapshot: true },
          }),
        );
      } else {
        connectWs();
      }
    },
    [connectWs],
  );

  const unsubscribe = useCallback((pair: string) => {
    pairsRef.current.delete(pair);
    delete booksRef.current[pair];
    dirtyRef.current = true;
    setSubscribedPairs([...pairsRef.current]);

    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          method: "unsubscribe",
          params: { channel: "book", symbol: [pair], depth: DEPTH },
        }),
      );
    }

    if (pairsRef.current.size === 0) {
      ws?.close();
    }
  }, []);

  const value = useMemo(
    () => ({
      connectionStatus,
      lastUpdated,
      orderbook: orderbooks,
      subscribe,
      unsubscribe,
      subscribedPairs,
    }),
    [connectionStatus, lastUpdated, orderbooks, subscribe, unsubscribe, subscribedPairs],
  );

  return (
    <KrakenWsContext.Provider value={value}>
      {children}
    </KrakenWsContext.Provider>
  );
}

export function useKrakenWs(): KrakenWsContextValue {
  const ctx = useContext(KrakenWsContext);
  if (!ctx)
    throw new Error("useKrakenWs must be used within <KrakenWsProvider>");
  return ctx;
}
