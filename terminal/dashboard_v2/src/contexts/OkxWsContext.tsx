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
  OkxBookMessage,
  OkxRawLevel,
} from "../types/orderbook";

const OKX_WS_URL = "wss://wsus.okx.com:8443/ws/v5/public";
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

export interface OkxWsContextValue {
  connectionStatus: ConnectionStatus;
  lastUpdated: Date | null;
  orderbook: Record<string, OrderbookData>;
  subscribe: (pair: string) => void;
  unsubscribe: (pair: string) => void;
  subscribedPairs: string[];
}

const OkxWsContext = createContext<OkxWsContextValue | null>(null);

function toNativePair(pair: string): string {
  const [base, quote] = pair.split("/");
  return `${base}-${quote === "USD" ? "USDT" : quote}`;
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

export function OkxWsProvider({ children }: { children: ReactNode }) {
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
    const socket = new WebSocket(OKX_WS_URL);
    wsRef.current = socket;

    socket.onopen = () => {
      if (wsRef.current !== socket) return;
      setConnectionStatus("connected");
      retriesRef.current = 0;
      for (const pair of pairsRef.current) {
        socket.send(
          JSON.stringify({
            op: "subscribe",
            args: [{ channel: "books", instId: toNativePair(pair) }],
          }),
        );
      }
    };

    socket.onmessage = (ev: MessageEvent) => {
      if (wsRef.current !== socket) return;
      try {
        const raw = JSON.parse(ev.data as string);
        if ("event" in raw) return;
        const msg = raw as OkxBookMessage;
        if (!msg.data || !msg.action) return;

        const d = msg.data[0];
        const nPair = fromNativePair(msg.arg.instId);
        if (!pairsRef.current.has(nPair)) return;

        if (msg.action === "snapshot") {
          booksRef.current[nPair] = {
            symbol: nPair,
            bids: parseOkxLevels(d.bids).slice(0, DEPTH),
            asks: parseOkxLevels(d.asks).slice(0, DEPTH),
            checksum: d.checksum,
          };
          dirtyRef.current = true;
        } else if (msg.action === "update" && booksRef.current[nPair]) {
          const cur = booksRef.current[nPair];
          booksRef.current[nPair] = {
            ...cur,
            bids:
              d.bids.length > 0
                ? applyLevelUpdate(cur.bids, parseOkxLevels(d.bids), true)
                : cur.bids,
            asks:
              d.asks.length > 0
                ? applyLevelUpdate(cur.asks, parseOkxLevels(d.asks), false)
                : cur.asks,
            checksum: d.checksum,
          };
          dirtyRef.current = true;
        }
      } catch(error){
        console.error("Failed to parse OKX message:", error);
      }
    };

    socket.onerror = () => {
      /* onclose will handle reconnection */
    };

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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  const subscribe = useCallback(
    (pair: string) => {
      const isNew = !pairsRef.current.has(pair);
      if (isNew) {
        pairsRef.current.add(pair);
        setSubscribedPairs([...pairsRef.current]);
      }

      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        if (isNew) {
          ws.send(
            JSON.stringify({
              op: "subscribe",
              args: [{ channel: "books", instId: toNativePair(pair) }],
            }),
          );
        }
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
          op: "unsubscribe",
          args: [{ channel: "books", instId: toNativePair(pair) }],
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
    <OkxWsContext.Provider value={value}>{children}</OkxWsContext.Provider>
  );
}

export function useOkxWs(): OkxWsContextValue {
  const ctx = useContext(OkxWsContext);
  if (!ctx) throw new Error("useOkxWs must be used within <OkxWsProvider>");
  return ctx;
}
