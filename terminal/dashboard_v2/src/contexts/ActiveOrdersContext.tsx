import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQueries } from "@tanstack/react-query";
import { fetchOrders } from "../api/orders";
import type { Exchange } from "../types/orderbook";
import type { Order } from "../types/orders";

interface ActiveOrdersContextValue {
  hasOrderAtPrice: (exchange: Exchange, pair: string, price: number) => boolean;
}

const ActiveOrdersContext = createContext<ActiveOrdersContextValue | null>(null);

const ACTIVE_STATUSES = new Set(["open", "pending", "live"]);

function isActiveLimitOrder(order: Order): boolean {
  return (
    order.type === "limit" &&
    order.price != null &&
    ACTIVE_STATUSES.has(order.status)
  );
}

function normalizePrice(price: number | string): number {
  return Math.round(Number(price) * 1e8) / 1e8;
}

function buildPriceKey(exchange: string, pair: string, price: number | string): string {
  return `${exchange}:${pair}:${normalizePrice(price)}`;
}

interface Props {
  configuredPairs: Record<Exchange, string[]>;
  children: ReactNode;
}

export function ActiveOrdersProvider({ configuredPairs, children }: Props) {
  const queries = useMemo(() => {
    const result: { exchange: Exchange; pair: string }[] = [];
    // TODO: uncomment kraken when backend REST is working
    // for (const pair of configuredPairs.kraken) {
    //   result.push({ exchange: "kraken", pair });
    // }
    for (const pair of configuredPairs.okx) {
      result.push({ exchange: "okx", pair });
    }
    return result;
  }, [configuredPairs]);

  const orderQueries = useQueries({
    queries: queries.map(({ exchange, pair }) => ({
      queryKey: ["orders", exchange, pair],
      queryFn: () => fetchOrders(exchange, pair),
      staleTime: Infinity,
    })),
  });

  const activePrices = useMemo(() => {
    const set = new Set<string>();
    for (let i = 0; i < queries.length; i++) {
      const { exchange, pair } = queries[i];
      const orders = orderQueries[i]?.data;
      if (!orders) continue;
      for (const order of orders) {
        if (isActiveLimitOrder(order)) {
          set.add(buildPriceKey(exchange, pair, order.price!));
        }
      }
    }
    console.log("[ActiveOrders] activePrices set:", [...set]);
    return set;
  }, [queries, orderQueries]);

  const value = useMemo<ActiveOrdersContextValue>(
    () => ({
      hasOrderAtPrice: (exchange, pair, price) =>
        activePrices.has(buildPriceKey(exchange, pair, price)),
    }),
    [activePrices],
  );

  return (
    <ActiveOrdersContext.Provider value={value}>
      {children}
    </ActiveOrdersContext.Provider>
  );
}

export function useActiveOrders(): ActiveOrdersContextValue {
  const ctx = useContext(ActiveOrdersContext);
  if (!ctx)
    throw new Error(
      "useActiveOrders must be used within <ActiveOrdersProvider>",
    );
  return ctx;
}
