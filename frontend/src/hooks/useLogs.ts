import { useQuery } from "@tanstack/react-query";
import type { LogFilters, LogPage } from "../types/reporting";
import { fetchLogs } from "../api/reporting";

/**
 * Fetches one page of the audit log for the given filters (including
 * `cursor`, when paging past the first page). Pagination is server-side
 * keyset (`next_cursor`), not a client-side sort/filter over one batch.
 */
export function useLogs(filters: LogFilters) {
  return useQuery<LogPage>({
    queryKey: ["reporting", "logs", filters],
    queryFn: () => fetchLogs(filters),
    staleTime: 15_000,
    retry: false,
  });
}
