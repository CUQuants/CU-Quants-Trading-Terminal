import { useQuery } from "@tanstack/react-query";
import { fetchOrders } from "../api/orders";
import type { Exchange } from "../types/orderbook";
import { hasBackend } from "../types/orderbook";

export function useOrders(exchange: Exchange, pair: string) {
  return useQuery({
    queryKey: ["orders", exchange, pair],
    queryFn: () => fetchOrders(exchange, pair),
    enabled: hasBackend(exchange),
  });
}
