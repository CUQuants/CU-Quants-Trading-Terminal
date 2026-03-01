import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { Exchange } from "../types/orderbook";
import type { Trade } from "../types/trades";
import { fetchTrades } from "../api/trades";

/**
 * Fetches trades from every active exchange in parallel and merges them into a
 * single list sorted by timestamp descending (most recent first).
 * Exchanges that fail are caught individually so successful ones still display.
 */
export function useTrades(activeExchanges: Exchange[]) {
  const key = activeExchanges.slice().sort().join(",");

  return useQuery<Trade[]>({
    queryKey: ["trades", key],
    queryFn: async () => {
      const failed: Exchange[] = [];

      const results = await Promise.all(
        activeExchanges.map((exchange) =>
          fetchTrades(exchange).catch(() => {
            failed.push(exchange);
            return [] as Trade[];
          }),
        ),
      );

      if (failed.length > 0) {
        const names = failed.map((e) => e.charAt(0).toUpperCase() + e.slice(1));
        toast.error(`Failed to fetch trades from: ${names.join(", ")}`);
      }

      return results
        .flat()
        .sort((a, b) => Number(b.timestamp) - Number(a.timestamp));
    },
    enabled: activeExchanges.length > 0,
    staleTime: 30_000,
  });
}
