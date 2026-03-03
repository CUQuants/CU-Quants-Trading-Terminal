import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { Exchange } from "../types/orderbook";
import type { AllBalances } from "../types/account";
import { fetchAllBalances } from "../api/account";

/**
 * Fetches all balances for each active exchange in parallel.
 * Failed exchanges are caught and toasts; successful data is returned.
 */
export function useAccountBalances(activeExchanges: Exchange[]) {
  const key = activeExchanges.slice().sort().join(",");

  return useQuery<Record<Exchange, AllBalances>>({
    queryKey: ["account", "balances", key],
    queryFn: async () => {
      const failed: Exchange[] = [];
      const results = await Promise.all(
        activeExchanges.map(async (exchange) => {
          try {
            const data = await fetchAllBalances(exchange);
            return { exchange, data } as const;
          } catch {
            failed.push(exchange);
            return { exchange, data: null } as const;
          }
        }),
      );

      if (failed.length > 0) {
        const names = failed.map((e) => e.charAt(0).toUpperCase() + e.slice(1));
        toast.error(`Failed to fetch balances from: ${names.join(", ")}`);
      }

      const out = {} as Record<Exchange, AllBalances>;
      for (const { exchange, data } of results) {
        if (data) out[exchange] = data;
      }
      return out;
    },
    enabled: activeExchanges.length > 0,
    staleTime: 30_000,
  });
}
