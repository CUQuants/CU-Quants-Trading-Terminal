import { useQuery } from "@tanstack/react-query";
import type { Exchange } from "../types/orderbook";
import { hasBackend } from "../types/orderbook";
import { fetchAvailablePositions } from "../api/account";

/**
 * Fetches available position (base currency) for a pair. Refetches every time
 * the component mounts (e.g. when the order panel opens).
 */
export function useAvailablePositions(exchange: Exchange, pair: string) {
  return useQuery({
    queryKey: ["account", "positions", exchange, pair],
    queryFn: () => fetchAvailablePositions(exchange, pair),
    enabled: !!exchange && !!pair && hasBackend(exchange),
    staleTime: 0,
    refetchOnMount: "always",
  });
}
