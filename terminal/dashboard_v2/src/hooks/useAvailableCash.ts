import { useQuery } from "@tanstack/react-query";
import type { Exchange } from "../types/orderbook";
import { fetchAvailableCash } from "../api/account";

/**
 * Fetches available cash (quote currency) for a pair. Refetches every time
 * the component mounts (e.g. when the order panel opens).
 */
export function useAvailableCash(exchange: Exchange, pair: string) {
  return useQuery({
    queryKey: ["account", "cash", exchange, pair],
    queryFn: () => fetchAvailableCash(exchange, pair),
    enabled: !!exchange && !!pair,
    staleTime: 0,
    refetchOnMount: "always",
  });
}
