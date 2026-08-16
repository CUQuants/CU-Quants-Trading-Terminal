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
import toast from "react-hot-toast";
import type { OrderbookData, OrderbookLevel } from "../types/orderbook";

const DEPTH = 25;
const FLUSH_INTERVAL_MS = 500;
const MAX_RETRIES = 3;
const BACKOFF_MS = [1000, 2000, 4000];

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "failed";

export interface ExchangeWsContextValue {
  connectionStatus: ConnectionStatus;
  lastUpdated: Date | null;
  orderbook: Record<string, OrderbookData>;
  /** Map of pair -> last subscription/error message (if any). */
  pairErrors: Record<string, string>;
  subscribe: (pair: string) => void;
  unsubscribe: (pair: string) => void;
  subscribedPairs: string[];
}

export interface NormalizedUpdate {
  pair: string;
  /** Exchange instrument ID (e.g. OKX instId) for resolving to subscribed pair key */
  instId?: string;
  type: "snapshot" | "update";
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  checksum?: number;
}

export type NormalizedErrorScope = "pair" | "connection";

export interface NormalizedError {
  type: "error";
  scope: NormalizedErrorScope;
  /** Normalized pair (e.g. BTC/USD) if error is scoped to a specific instrument. */
  pair?: string;
  /** Exchange-specific error code, if provided. */
  code?: string;
  /** Human-readable message suitable for display to the user. */
  message: string;
  /** Optional raw payload for debugging. */
  raw?: unknown;
}

export type NormalizedMessage = NormalizedUpdate | NormalizedError;

export interface ExchangeWsAdapter {
  name: string;
  wsUrl: string;
  toWirePair(pair: string): string;
  buildSubscribeMsg(wirePairs: string[]): unknown;
  buildUnsubscribeMsg(wirePairs: string[]): unknown;
  /** Parse a raw WS frame into a normalized update or error. */
  parseMessage(raw: unknown): NormalizedMessage | null;
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

export function createExchangeWsContext(adapter: ExchangeWsAdapter) {
  const Ctx = createContext<ExchangeWsContextValue | null>(null);
  Ctx.displayName = `${adapter.name}WsContext`;

  function Provider({ children }: { children: ReactNode }) {
    const [connectionStatus, setConnectionStatus] =
      useState<ConnectionStatus>("disconnected");
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [orderbooks, setOrderbooks] = useState<
      Record<string, OrderbookData>
    >({});
    const [subscribedPairs, setSubscribedPairs] = useState<string[]>([]);
    const [pairErrors, setPairErrors] = useState<Record<string, string>>({});

    const wsRef = useRef<WebSocket | null>(null);
    const booksRef = useRef<Record<string, OrderbookData>>({});
    const dirtyRef = useRef(false);
    const pairsRef = useRef<Set<string>>(new Set());
    const retriesRef = useRef(0);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const connectWs = useCallback(() => {
      if (pairsRef.current.size === 0) return;
      const ws = wsRef.current;
      if (
        ws &&
        (ws.readyState === WebSocket.OPEN ||
          ws.readyState === WebSocket.CONNECTING)
      )
        return;

      setConnectionStatus("connecting");
      const socket = new WebSocket(adapter.wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        if (wsRef.current !== socket) return;
        setConnectionStatus("connected");
        retriesRef.current = 0;

        const wirePairs = [...pairsRef.current].map((p) =>
          adapter.toWirePair(p),
        );
        if (wirePairs.length > 0) {
          socket.send(JSON.stringify(adapter.buildSubscribeMsg(wirePairs)));
        }
      };

      socket.onmessage = (ev: MessageEvent) => {
        if (wsRef.current !== socket) return;
        try {
          const raw: unknown = JSON.parse(ev.data as string);
          const parsed = adapter.parseMessage(raw);
          if (!parsed) return;

          if (parsed.type === "error") {
            // Log full error for debugging.
            // eslint-disable-next-line no-console
            console.error(`[${adapter.name} WS error]`, parsed.raw ?? parsed);

            if (parsed.scope === "pair" && parsed.pair) {
              setPairErrors((prev) => ({
                ...prev,
                [parsed.pair as string]: parsed.message,
              }));
            } else if (parsed.scope === "connection") {
              setConnectionStatus("failed");
            }

            toast.error(parsed.message);
            return;
          }

          const { pair, instId, type, bids, asks, checksum } = parsed;
          const key =
            instId &&
            [...pairsRef.current].find(
              (p) =>
                adapter.toWirePair(p).toUpperCase() === instId.toUpperCase(),
            );
          const storageKey = (key ?? pair) as string;
          if (!pairsRef.current.has(storageKey)) return;

          // Clear any previous error for this pair once we receive valid data.
          setPairErrors((prev) => {
            if (!prev[storageKey]) return prev;
            const { [storageKey]: _removed, ...rest } = prev;
            return rest;
          });

          if (type === "snapshot") {
            booksRef.current[storageKey] = {
              symbol: storageKey,
              bids: bids
                .sort((a, b) => b.price - a.price)
                .slice(0, DEPTH),
              asks: asks
                .sort((a, b) => a.price - b.price)
                .slice(0, DEPTH),
              checksum,
            };
            dirtyRef.current = true;
          } else if (type === "update" && booksRef.current[storageKey]) {
            const cur = booksRef.current[storageKey];
            booksRef.current[storageKey] = {
              ...cur,
              bids:
                bids.length > 0
                  ? applyLevelUpdate(cur.bids, bids, true)
                  : cur.bids,
              asks:
                asks.length > 0
                  ? applyLevelUpdate(cur.asks, asks, false)
                  : cur.asks,
              checksum,
            };
            dirtyRef.current = true;
          }
        } catch {
          /* malformed message — skip */
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
        const isNew = !pairsRef.current.has(pair);
        if (isNew) {
          pairsRef.current.add(pair);
          setSubscribedPairs([...pairsRef.current]);
        }

        const ws = wsRef.current;
        if (ws?.readyState === WebSocket.OPEN) {
          if (isNew) {
            ws.send(
              JSON.stringify(
                adapter.buildSubscribeMsg([adapter.toWirePair(pair)]),
              ),
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
          JSON.stringify(
            adapter.buildUnsubscribeMsg([adapter.toWirePair(pair)]),
          ),
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
        pairErrors,
        subscribe,
        unsubscribe,
        subscribedPairs,
      }),
      [
        connectionStatus,
        lastUpdated,
        orderbooks,
        pairErrors,
        subscribe,
        unsubscribe,
        subscribedPairs,
      ],
    );

    return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
  }

  Provider.displayName = `${adapter.name}WsProvider`;

  function useExchangeWs(): ExchangeWsContextValue {
    const ctx = useContext(Ctx);
    if (!ctx)
      throw new Error(
        `use${adapter.name}Ws must be used within <${adapter.name}WsProvider>`,
      );
    return ctx;
  }

  return { Provider, useExchangeWs };
}
