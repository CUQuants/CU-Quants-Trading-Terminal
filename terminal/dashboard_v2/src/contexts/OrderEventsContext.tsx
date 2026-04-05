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
import toast from "react-hot-toast";
import type { Exchange } from "../types/orderbook";
import { hasBackend } from "../types/orderbook";
import type { BackendWsMessage, Order, OrderEvent } from "../types/orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const MAX_RETRIES = 3;
const BACKOFF_MS = [1000, 2000, 4000];
const HEARTBEAT_CHECK_MS = 500;
const ORDER_EVENT_SILENCE_MS = 3000;
const PONG_TIMEOUT_MS = 2000;

const TERMINAL_STATUSES = new Set(["filled", "canceled"]);

type EventsStatus =
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "idle"
  | "dead";

export interface OrderEventsContextValue {
  orderEventsStatus: Record<Exchange, EventsStatus>;
}

const OrderEventsContext = createContext<OrderEventsContextValue | null>(null);

interface Props {
  activeExchanges: Exchange[];
  children: ReactNode;
}

function applyOrderEvent(prev: Order[] | undefined, event: OrderEvent): Order[] {
  const orders = prev ?? [];

  if (TERMINAL_STATUSES.has(event.status)) {
    return orders.filter((o) => o.id !== event.orderId);
  }

  const idx = orders.findIndex((o) => o.id === event.orderId);
  if (idx !== -1) {
    const updated = [...orders];
    updated[idx] = {
      ...updated[idx],
      status: event.status,
      price: event.price || updated[idx].price,
      size: event.size || updated[idx].size,
    };
    return updated;
  }

  return [
    ...orders,
    {
      id: event.orderId,
      pair: event.pair,
      exchange: event.exchange,
      side: event.side as Order["side"],
      type: "limit",
      price: event.price,
      size: event.size,
      status: event.status,
      created_at: event.timestamp,
    },
  ];
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
  const heartbeatIntervals = useRef<Record<string, ReturnType<typeof setInterval>>>(
    {},
  );
  const pongTimeouts = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const pendingPingIds = useRef<Record<string, string | undefined>>({});
  const lastOrderEventAtRef = useRef<Record<string, number>>({});
  const lastPingAtRef = useRef<Record<string, number>>({});
  const deadNotificationShown = useRef<Record<string, boolean>>({});
  const closingRef = useRef<Set<string>>(new Set());

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
    clearHeartbeat(exchange);
    lastOrderEventAtRef.current[exchange] = Date.now();
    lastPingAtRef.current[exchange] = 0;
    deadNotificationShown.current[exchange] = false;

    ws.onopen = () => {
      const wasReconnect = (retriesMapRef.current[exchange] ?? 0) > 0;
      retriesMapRef.current[exchange] = 0;
      setStatus((prev) => ({ ...prev, [exchange]: "connected" }));
      startHeartbeat(exchange, ws);

      if (wasReconnect) {
        queryClient.invalidateQueries({
          queryKey: ["orders", exchange],
        });
      }
    };

    ws.onmessage = (ev: MessageEvent) => {
      try {
        const data: BackendWsMessage = JSON.parse(ev.data as string);

        if (data.type === "order_event") {
          lastOrderEventAtRef.current[exchange] = Date.now();
          queryClient.setQueryData<Order[]>(
            ["orders", exchange, data.pair],
            (prev) => applyOrderEvent(prev, data),
          );
        } else if (data.type === "status") {
          setStatus((prev) => ({
            ...prev,
            [exchange]: data.connectionStatus,
          }));
        } else if (
          data.type === "pong" &&
          data.id === pendingPingIds.current[exchange]
        ) {
          clearPongTimeout(exchange);
          pendingPingIds.current[exchange] = undefined;
          deadNotificationShown.current[exchange] = false;
          setStatus((prev) => {
            if (prev[exchange] !== "dead") {
              return prev;
            }
            return { ...prev, [exchange]: "connected" };
          });
        }
      } catch {
        /* ignore malformed */
      }
    };

    ws.onerror = () => {};

    ws.onclose = () => {
      clearHeartbeat(exchange);
      delete wsMapRef.current[exchange];

      if (closingRef.current.has(exchange)) {
        closingRef.current.delete(exchange);
        return;
      }

      if (!deadNotificationShown.current[exchange]) {
        deadNotificationShown.current[exchange] = true;
        toast.error(
          `${exchange.toUpperCase()} order events connection closed unexpectedly.`,
        );
      }

      const retries = (retriesMapRef.current[exchange] ?? 0) + 1;
      retriesMapRef.current[exchange] = retries;

      if (retries > MAX_RETRIES) {
        setStatus((prev) => ({ ...prev, [exchange]: "disconnected" }));
        return;
      }

      setStatus((prev) => ({ ...prev, [exchange]: "dead" }));
      const delay = BACKOFF_MS[Math.min(retries - 1, BACKOFF_MS.length - 1)];
      reconnectTimers.current[exchange] = setTimeout(
        () => {
          setStatus((prev) => ({ ...prev, [exchange]: "reconnecting" }));
          connectExchange(exchange);
        },
        delay,
      );
    };
  }

  function startHeartbeat(exchange: Exchange, ws: WebSocket) {
    heartbeatIntervals.current[exchange] = setInterval(() => {
      if (
        ws.readyState !== WebSocket.OPEN ||
        pendingPingIds.current[exchange] !== undefined
      ) {
        return;
      }

      const lastOrderEventAt = lastOrderEventAtRef.current[exchange] ?? 0;
      const now = Date.now();

      if (now - lastOrderEventAt < ORDER_EVENT_SILENCE_MS) {
        return;
      }

      if (now - (lastPingAtRef.current[exchange] ?? 0) < ORDER_EVENT_SILENCE_MS) {
        return;
      }

      const pingId = `${exchange}-${now}`;
      lastPingAtRef.current[exchange] = now;
      pendingPingIds.current[exchange] = pingId;

      try {
        ws.send(JSON.stringify({ type: "ping", id: pingId }));
      } catch {
        pendingPingIds.current[exchange] = undefined;
        return;
      }

      pongTimeouts.current[exchange] = setTimeout(() => {
        if (pendingPingIds.current[exchange] !== pingId) {
          return;
        }

        pendingPingIds.current[exchange] = undefined;
        setStatus((prev) => ({ ...prev, [exchange]: "dead" }));

        if (!deadNotificationShown.current[exchange]) {
          deadNotificationShown.current[exchange] = true;
          toast.error(`${exchange.toUpperCase()} order events connection is dead.`);
        }
      }, PONG_TIMEOUT_MS);
    }, HEARTBEAT_CHECK_MS);
  }

  function clearPongTimeout(exchange: Exchange) {
    if (pongTimeouts.current[exchange]) {
      clearTimeout(pongTimeouts.current[exchange]);
      delete pongTimeouts.current[exchange];
    }
  }

  function clearHeartbeat(exchange: Exchange) {
    if (heartbeatIntervals.current[exchange]) {
      clearInterval(heartbeatIntervals.current[exchange]);
      delete heartbeatIntervals.current[exchange];
    }

    clearPongTimeout(exchange);
    pendingPingIds.current[exchange] = undefined;
  }

  function closeExchange(exchange: Exchange) {
    if (reconnectTimers.current[exchange]) {
      clearTimeout(reconnectTimers.current[exchange]);
      delete reconnectTimers.current[exchange];
    }
    clearHeartbeat(exchange);
    closingRef.current.add(exchange);
    wsMapRef.current[exchange]?.close();
    delete wsMapRef.current[exchange];
    delete lastOrderEventAtRef.current[exchange];
    delete lastPingAtRef.current[exchange];
    delete deadNotificationShown.current[exchange];
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
