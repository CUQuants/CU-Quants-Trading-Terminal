import { useEffect, useState } from "react";
import { useNews } from "../hooks/useNews";
import { NewsApiError } from "../api/news";
import { DEFAULT_NEWS_VIEW_STATE, type NewsFilters, type NewsViewState } from "../types/news";
import { ArticleCard, NewsEventCard, NewsTime } from "./news/NewsCards";
import { NewsFilters as NewsFilterControls } from "./news/NewsFilters";
import { NewsProviderStatus } from "./news/NewsProviderStatus";

interface Props {
  configuredPairs: string[];
  state: NewsViewState;
  onStateChange: (state: NewsViewState) => void;
}

export function NewsView({ configuredPairs, state, onStateChange }: Props) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const update = () => setNow(Date.now());
    const timer = setInterval(update, 15_000);
    document.addEventListener("visibilitychange", update);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", update);
    };
  }, []);

  const pairs = configuredPairs.length === 0 || state.pairScope === "all" ? []
    : state.pairScope === "configured" ? configuredPairs
    : state.selectedPairs.filter((pair) => configuredPairs.includes(pair));
  const needsPairSelection = configuredPairs.length > 0 && state.pairScope === "selected" && pairs.length === 0;
  const filters: NewsFilters = {
    category: state.category,
    source: state.source,
    timeframe: state.timeframe,
    pairs,
  };
  const { articles, events, status } = useNews(filters, state.mode, !needsPairSelection);
  const feed = state.mode === "events" ? events : articles;
  const data = feed.data;
  const isStale = data != null && (data.lastSuccessfulRefreshAt === null
    || now - Date.parse(data.lastSuccessfulRefreshAt) >= data.staleAfterSeconds * 1000);
  const isRefreshing = feed.isFetching || status.isFetching;
  const categoryLabel = (id: string) => status.data?.categories.find((category) => category.id === id)?.label ?? id;

  function refresh() {
    if (!needsPairSelection) void feed.refetch();
    void status.refetch();
  }

  return (
    <main className="flex-1 min-w-0" aria-label="News">
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5">
        <div>
          <h1 className="text-lg font-semibold">News</h1>
          <p className="mt-1 text-xs text-white/45">Market reports, related events, and source-backed context.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="text-white/40">Refreshes every 45 seconds while visible</span>
          <button type="button" onClick={refresh} disabled={isRefreshing}
            className="rounded-md border border-white/15 px-3 py-2 text-white/75 hover:bg-white/5 cursor-pointer disabled:opacity-40 disabled:cursor-default">
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      <NewsFilterControls state={state} configuredPairs={configuredPairs} status={status.data} onChange={onStateChange} />

      <div className="px-6 py-4 space-y-4">
        <NewsProviderStatus data={status.data} isError={status.isError} now={now} />

        {!needsPairSelection && data && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-white/45">
              <span>Showing {data.items.length} of {data.total} {state.mode}
                {data.total > data.items.length ? " · Latest results only; narrow filters for more specific coverage" : ""}</span>
              <span>Last successful collection: <NewsTime value={data.lastSuccessfulRefreshAt} now={now} /></span>
            </div>
            {isStale && (
              <p role="status" className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200">
                {data.lastSuccessfulRefreshAt === null
                  ? "The news service has not completed a successful collection yet."
                  : "News data is stale. Showing the last collected reports; newer developments may be missing."}
              </p>
            )}
            {feed.isError && (
              <p role="status" className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-200">
                News refresh failed. Previously loaded results are still shown. Use Refresh to try again.
              </p>
            )}
          </div>
        )}

        {needsPairSelection ? (
          <div role="status" className="py-16 text-center text-sm text-white/50">Choose at least one configured pair above, or select All news.</div>
        ) : feed.isPending ? (
          <div role="status" aria-label="Loading news" className="space-y-4">
            <p className="text-sm text-white/50">Loading news…</p>
            {[0, 1, 2].map((index) => (
              <div key={index} aria-hidden="true" className="rounded-xl border border-white/10 p-5 space-y-4 animate-pulse motion-reduce:animate-none">
                <div className="h-3 w-32 rounded bg-white/10" />
                <div className="h-5 w-3/4 rounded bg-white/10" />
                <div className="h-3 w-1/2 rounded bg-white/5" />
              </div>
            ))}
          </div>
        ) : !data ? (
          <div role="status" className="rounded-xl border border-white/10 py-16 px-6 text-center">
            <h2 className="text-base text-white/75">News unavailable</h2>
            <p className="mt-2 text-sm text-white/45">
              {feed.error instanceof NewsApiError ? feed.error.message : "The news service could not be reached. Try refreshing shortly."}
            </p>
          </div>
        ) : data.items.length === 0 ? (
          <div role="status" className="py-16 text-center">
            <h2 className="text-base text-white/75">{data.lastSuccessfulRefreshAt === null ? "Waiting for news" : "No news matches these filters"}</h2>
            <p className="mt-2 text-sm text-white/45">Try a wider timeframe or all news.</p>
            <button type="button" onClick={() => onStateChange({ ...DEFAULT_NEWS_VIEW_STATE, mode: state.mode, pairScope: "all" })}
              className="mt-4 rounded-md border border-white/15 px-3 py-2 text-xs text-white/75 hover:bg-white/5 cursor-pointer">
              Clear filters
            </button>
          </div>
        ) : state.mode === "events" ? (
          <div className="space-y-4">
            {events.data?.items.map((event) => <NewsEventCard key={event.id} event={event} now={now} categoryLabel={categoryLabel(event.category)} />)}
          </div>
        ) : (
          <div className="space-y-4">
            {articles.data?.items.map((article) => <ArticleCard key={article.id} article={article} now={now} categoryLabel={categoryLabel(article.category)} />)}
          </div>
        )}
      </div>
    </main>
  );
}
