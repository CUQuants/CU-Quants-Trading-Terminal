import { useQuery } from "@tanstack/react-query";
import { fetchNews, fetchNewsEvents, fetchNewsStatus, NewsApiError, NEWS_LIMIT } from "../api/news";
import type { NewsFilters, NewsMode } from "../types/news";

const queryOptions = {
  staleTime: 30_000,
  refetchInterval: 45_000,
  refetchIntervalInBackground: false,
  refetchOnWindowFocus: "always" as const,
  retry: (failureCount: number, error: Error) => {
    if (error instanceof NewsApiError && (error.status < 500 || error.status === 501)) return false;
    return failureCount < 1;
  },
};

/** Mounted only in NewsView; inactive feed modes never poll. */
export function useNews(filters: NewsFilters, mode: NewsMode, enabled = true) {
  const normalizedFilters = { ...filters, pairs: [...new Set(filters.pairs)].sort() };
  const keyFilters = { ...normalizedFilters, limit: NEWS_LIMIT };

  const articles = useQuery({
    ...queryOptions,
    queryKey: ["news", "articles", keyFilters],
    queryFn: ({ signal }) => fetchNews(normalizedFilters, signal),
    enabled: enabled && mode === "articles",
  });
  const events = useQuery({
    ...queryOptions,
    queryKey: ["news", "events", keyFilters],
    queryFn: ({ signal }) => fetchNewsEvents(normalizedFilters, signal),
    enabled: enabled && mode === "events",
  });
  const status = useQuery({
    ...queryOptions,
    queryKey: ["news", "status"],
    queryFn: ({ signal }) => fetchNewsStatus(signal),
  });

  return { articles, events, status };
}
