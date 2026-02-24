import {
  createContext,
  useContext,
  useRef,
  useState,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Exchange } from "../types/orderbook";
import type { BackendWsMessage } from "../types/orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const FLUSH_INTERVAL_MS = 500;
const MAX_RETRIES = 3;
const BACKOFF_MS = [1000, 2000, 4000];

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
  });

  const wsMapRef = useRef<Record<string, WebSocket>>({});
  const retriesMapRef = useRef<Record<string, number>>({});
  const reconnectTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const pendingRef = useRef<Map<string, Set<string>>>(new Map());
  const closingRef = useRef<Set<string>>(new Set());

  // Batched invalidation: every 500ms, flush accumulated pair keys
  useEffect(() => {
    const id = setInterval(() => {
      const map = pendingRef.current;
      if (map.size === 0) return;

      for (const [exchange, pairs] of map.entries()) {
        for (const pair of pairs) {
          queryClient.invalidateQueries({
            queryKey: ["orders", exchange, pair],
          });
        }
      }
      map.clear();
    }, FLUSH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [queryClient]);

  // Connect / disconnect based on activeExchanges
  useEffect(() => {
    const activeSet = new Set(activeExchanges);

    // Open connections for newly active exchanges
    for (const exchange of activeExchanges) {
      if (!wsMapRef.current[exchange]) {
        connectExchange(exchange);
      }
    }

    // Close connections for exchanges no longer active
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
          const pairs =
            pendingRef.current.get(exchange) ?? new Set<string>();
          pairs.add(data.pair);
          pendingRef.current.set(exchange, pairs);
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
