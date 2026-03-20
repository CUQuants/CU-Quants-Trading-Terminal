import {
  createContext,
  useContext,
  useRef,
  useState,
  useEffect,
  useMemo,
  useCallback,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Exchange } from "../types/orderbook";
import { hasBackend } from "../types/orderbook";
import type { BackendWsMessage } from "../types/orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const MAX_RETRIES = 3;
const BACKOFF_MS = [1000, 2000, 4000];
const INVALIDATION_INTERVAL_MS = 500;

type EventsStatus = "connected" | "reconnecting" | "disconnected" | "idle";

export interface OrderEventsContextValue {
  orderEventsStatus: Record<Exchange, EventsStatus>;
}

const OrderEventsContext = createContext<OrderEventsContextValue | null>(null);

interface Props {
  activeExchanges: Exchange[];
  children: ReactNode;
}

export function OrderEventsProvider({ activeExchanges, children }: Props) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Record<Exchange, EventsStatus>>({
    kraken: "idle",
    okx: "idle",
    gemini: "idle",
  });

  const wsMapRef = useRef<Record<string, WebSocket>>({});
  const retriesMapRef = useRef<Record<string, number>>({});
  const reconnectTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const closingRef = useRef<Set<string>>(new Set());

  // Pending invalidation keys accumulated between flushes.
  // Each entry is a serialised query key like "orders|kraken|BTC/USD".
  const pendingInvalidations = useRef<Map<string, readonly [string, string]>>(
    new Map(),
  );

  const flushInvalidations = useCallback(() => {
    if (pendingInvalidations.current.size === 0) return;

    const batch = new Map(pendingInvalidations.current);
    pendingInvalidations.current.clear();

    for (const [exchange, pair] of batch.values()) {
      queryClient.invalidateQueries({
        queryKey: ["orders", exchange, pair],
      });
    }
  }, [queryClient]);

  // Interval that flushes pending invalidations every INVALIDATION_INTERVAL_MS
  useEffect(() => {
    const id = setInterval(flushInvalidations, INVALIDATION_INTERVAL_MS);
    return () => clearInterval(id);
  }, [flushInvalidations]);

  // Connect / disconnect based on activeExchanges
  useEffect(() => {
    const activeSet = new Set(activeExchanges);

    for (const exchange of activeExchanges) {
      if (hasBackend(exchange) && !wsMapRef.current[exchange]) {
        connectExchange(exchange);
      }
    }

    for (const exchange of Object.keys(wsMapRef.current)) {
      if (!activeSet.has(exchange as Exchange)) {
        closeExchange(exchange as Exchange);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeExchanges]);

  // Cleanup everything on unmount
  useEffect(() => {
    return () => {
      for (const exchange of Object.keys(wsMapRef.current)) {
        closeExchange(exchange as Exchange);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function connectExchange(exchange: Exchange) {
    const url = `${WS_BASE}/orders/${exchange}`;
    const ws = new WebSocket(url);
    wsMapRef.current[exchange] = ws;

    ws.onopen = () => {
      retriesMapRef.current[exchange] = 0;
      setStatus((prev) => ({ ...prev, [exchange]: "connected" }));
    };

    ws.onmessage = (ev: MessageEvent) => {
      try {
        const data: BackendWsMessage = JSON.parse(ev.data as string);

        if (data.type === "order_event") {
          const key = `${exchange}|${data.pair}`;
          pendingInvalidations.current.set(key, [exchange, data.pair]);
        } else if (data.type === "status") {
          setStatus((prev) => ({
            ...prev,
            [exchange]: data.connectionStatus,
          }));
        }
      } catch {
        /* ignore malformed */
      }
    };

    ws.onerror = () => {};

    ws.onclose = () => {
      delete wsMapRef.current[exchange];

      if (closingRef.current.has(exchange)) {
        closingRef.current.delete(exchange);
        return;
      }

      const retries = (retriesMapRef.current[exchange] ?? 0) + 1;
      retriesMapRef.current[exchange] = retries;

      if (retries > MAX_RETRIES) {
        setStatus((prev) => ({ ...prev, [exchange]: "disconnected" }));
        return;
      }

      setStatus((prev) => ({ ...prev, [exchange]: "reconnecting" }));
      const delay = BACKOFF_MS[Math.min(retries - 1, BACKOFF_MS.length - 1)];
      reconnectTimers.current[exchange] = setTimeout(
        () => connectExchange(exchange),
        delay,
      );
    };
  }

  function closeExchange(exchange: Exchange) {
    if (reconnectTimers.current[exchange]) {
      clearTimeout(reconnectTimers.current[exchange]);
      delete reconnectTimers.current[exchange];
    }
    closingRef.current.add(exchange);
    wsMapRef.current[exchange]?.close();
    delete wsMapRef.current[exchange];
    retriesMapRef.current[exchange] = 0;
    setStatus((prev) => ({ ...prev, [exchange]: "idle" }));
  }

  const value = useMemo(
    () => ({ orderEventsStatus: status }),
    [status],
  );

  return (
    <OrderEventsContext.Provider value={value}>
      {children}
    </OrderEventsContext.Provider>
  );
}

export function useOrderEvents(): OrderEventsContextValue {
  const ctx = useContext(OrderEventsContext);
  if (!ctx)
    throw new Error(
      "useOrderEvents must be used within <OrderEventsProvider>",
    );
  return ctx;
}
