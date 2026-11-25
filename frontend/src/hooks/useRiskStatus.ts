import { useQuery } from "@tanstack/react-query";
import type { RiskStatus } from "../types/risk";
import { fetchRiskStatus } from "../api/risk";

/** Polls the RMU's kill switch status. */
export function useRiskStatus(refreshMs: number | false = 5_000) {
  return useQuery<RiskStatus>({
    queryKey: ["risk"],
    queryFn: fetchRiskStatus,
    refetchInterval: refreshMs,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
