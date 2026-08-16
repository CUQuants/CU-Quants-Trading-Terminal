import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { Exchange } from "../types/orderbook";
import { hasBackend } from "../types/orderbook";
import type { AllPositions } from "../types/account";
import { fetchAllPositions } from "../api/account";

/**
 * Fetches all positions (non-zero, non-cash) for each active exchange in parallel.
 * Failed exchanges are caught and toasts; successful data is returned.
 */
export function useAccountPositions(activeExchanges: Exchange[]) {
  const supported = activeExchanges.filter(hasBackend);
  const key = supported.slice().sort().join(",");

  return useQuery<Record<Exchange, AllPositions>>({
    queryKey: ["account", "positions", key],
    queryFn: async () => {
      const failed: Exchange[] = [];
      const results = await Promise.all(
        supported.map(async (exchange) => {
          try {
            const data = await fetchAllPositions(exchange);
            return { exchange, data } as const;
          } catch {
            failed.push(exchange);
            return { exchange, data: null } as const;
          }
        }),
      );

      if (failed.length > 0) {
        const names = failed.map((e) => e.charAt(0).toUpperCase() + e.slice(1));
        toast.error(`Failed to fetch positions from: ${names.join(", ")}`);
      }

      const out = {} as Record<Exchange, AllPositions>;
      for (const { exchange, data } of results) {
        if (data) out[exchange] = data;
      }
      return out;
    },
    enabled: supported.length > 0,
    staleTime: 30_000,
  });
}
