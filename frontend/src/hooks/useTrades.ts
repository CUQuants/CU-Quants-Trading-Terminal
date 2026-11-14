import { useMemo } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { Exchange } from "../types/orderbook";
import { hasBackend } from "../types/orderbook";
import type { Trade } from "../types/trades";
import { fetchTrades } from "../api/trades";

/** Offset to fetch next, per exchange. Exchanges with no more fills are absent. */
type Cursors = Partial<Record<Exchange, number>>;

interface Page {
  trades: Trade[];
  next: Cursors;
}

/**
 * Fetches trades from every active exchange in parallel and merges them into a
 * single list sorted by timestamp descending (most recent first).
 *
 * The first page asks every exchange. `fetchNextPage` asks only the exchanges
 * that reported older fills (Kraken Prime today) and appends them.
 * Exchanges that fail are caught individually so successful ones still display.
 */
export function useTrades(activeExchanges: Exchange[]) {
  const supported = activeExchanges.filter(hasBackend);
  const key = supported.slice().sort().join(",");

  const query = useInfiniteQuery({
    queryKey: ["trades", key],
    initialPageParam: null as Cursors | null,
    queryFn: async ({ pageParam }): Promise<Page> => {
      const targets: [Exchange, number][] = pageParam
        ? (Object.entries(pageParam) as [Exchange, number][])
        : supported.map((e) => [e, 0]);
      const failed: Exchange[] = [];
      const next: Cursors = {};

      const results = await Promise.all(
        targets.map(([exchange, offset]) =>
          fetchTrades(exchange, { offset })
            .then((page) => {
              if (page.next_offset != null) next[exchange] = page.next_offset;
              return page.trades;
            })
            .catch(() => {
              failed.push(exchange);
              return [] as Trade[];
            }),
        ),
      );

      if (failed.length > 0) {
        const names = failed.map((e) => e.charAt(0).toUpperCase() + e.slice(1));
        toast.error(`Failed to fetch trades from: ${names.join(", ")}`);
      }

      return { trades: results.flat(), next };
    },
    getNextPageParam: (last) =>
      Object.keys(last.next).length > 0 ? last.next : undefined,
    enabled: supported.length > 0,
    staleTime: 30_000,
  });

  // Offsets shift when new fills land between pages, so the same fill can
  // come back twice. Keep the first copy.
  const data = useMemo(() => {
    if (!query.data) return undefined;
    const seen = new Set<string>();
    const merged: Trade[] = [];
    for (const page of query.data.pages) {
      for (const t of page.trades) {
        const id = `${t.exchange}:${t.id}`;
        if (seen.has(id)) continue;
        seen.add(id);
        merged.push(t);
      }
    }
    return merged.sort((a, b) => Number(b.timestamp) - Number(a.timestamp));
  }, [query.data]);

  return { ...query, data };
}
