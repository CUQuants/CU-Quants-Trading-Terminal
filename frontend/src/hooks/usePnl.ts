import { useQuery } from "@tanstack/react-query";
import type { PnlReport } from "../types/pnl";
import { fetchPnl } from "../api/pnl";

/** Polls the RMU's PnL report. Each read fetches a fresh mark per pair. */
export function usePnl(refreshMs: number | false = 5_000) {
  return useQuery<PnlReport>({
    queryKey: ["pnl"],
    queryFn: fetchPnl,
    refetchInterval: refreshMs,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
