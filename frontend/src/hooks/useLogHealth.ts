import { useQuery } from "@tanstack/react-query";
import type { LogHealth } from "../types/reporting";
import { fetchLogHealth } from "../api/reporting";

export function useLogHealth() {
  return useQuery<LogHealth>({
    queryKey: ["reporting", "health"],
    queryFn: fetchLogHealth,
    staleTime: 30_000,
    retry: false,
  });
}
