import { useEffect, useState } from "react";
import { useNews } from "../hooks/useNews";
import { NewsApiError } from "../api/news";
import { DEFAULT_NEWS_VIEW_STATE, type NewsFilters, type NewsViewState } from "../types/news";
import { NewsTime } from "./news/NewsCards";
import { NewsTable } from "./news/NewsTable";
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
    assets: state.assetQuery.split(",").map((asset) => asset.trim()).filter(Boolean),
  };
  const { articles, events, status } = useNews(filters, state.mode, !needsPairSelection);
  const feed = state.mode === "events" ? events : articles;
  const data = feed.data;
  const displayedPairs = [...new Set(configuredPairs)];
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
      <div className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-1 border-b border-white/10 px-4 py-2 min-[1800px]:flex min-[1800px]:gap-6 min-[1800px]:px-6 min-[1800px]:py-5">
        <div>
          <h1 className="text-lg font-semibold whitespace-nowrap">News Hub</h1>
        </div>
        <NewsFilterControls state={state} configuredPairs={configuredPairs} status={status.data} onChange={onStateChange} />
        <div className="flex justify-end items-center gap-2 text-xs min-[1800px]:gap-3">
          <NewsProviderStatus data={status.data} isError={status.isError} now={now} />
          <div className="hidden md:flex flex-col items-start gap-1 border-l border-white/15 pl-4 text-left text-white/45">
            {!needsPairSelection && data && <span>Showing {data.items.length} of {data.total} {state.mode}</span>}
            <span>Refreshes every 45 seconds while visible</span>
            {!needsPairSelection && data && (
              <span>Last successful collection: <NewsTime value={data.lastSuccessfulRefreshAt} now={now} /></span>
            )}
          </div>
          <button type="button" onClick={refresh} disabled={isRefreshing}
            className="rounded-md border border-white/15 px-3 py-2 text-white/75 hover:bg-white/5 cursor-pointer disabled:opacity-40 disabled:cursor-default">
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-white/10 bg-white/[0.03] px-4 py-1.5 text-xs text-white/50 [&>button]:shrink-0" aria-label="Configured pairs">
        {displayedPairs.length === 0 ? "No pairs configured." : (
          <>
            <span>Pairs:</span>
            {displayedPairs.map((pair) => {
              const isSelected = state.pairScope === "selected" && pairs.length === 1 && pairs[0] === pair;
              return (
                <button key={pair} type="button" aria-pressed={isSelected}
                  onClick={() => onStateChange({ ...state, pairScope: isSelected ? "all" : "selected", selectedPairs: isSelected ? [] : [pair] })}
                  className={`rounded border px-2 py-0.5 cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#2F71C8] ${isSelected ? "border-[#2F71C8] bg-[#2F71C8]/20 text-white" : "border-white/15 bg-white/[0.04] text-white/75 hover:border-[#2F71C8]/60 hover:text-white"}`}>
                  {pair}
                </button>
              );
            })}
          </>
        )}
      </div>

      <div>
        {!needsPairSelection && data && (data.total > data.items.length || isStale || feed.isError) && (
          <div className="px-4 py-3 space-y-3">
            {data.total > data.items.length && (
              <p className="text-xs text-white/45">Latest results only; narrow filters for more specific coverage.</p>
            )}
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
          <>
          <NewsTable items={[]} now={now} categoryLabel={categoryLabel} />
          <div role="status" className="py-16 text-center">
            <h2 className="text-base text-white/75">{data.lastSuccessfulRefreshAt === null ? "Waiting for news" : "No news matches these filters"}</h2>
            <p className="mt-2 text-sm text-white/45">Try a wider timeframe or all news.</p>
            <button type="button" onClick={() => onStateChange({ ...DEFAULT_NEWS_VIEW_STATE, mode: state.mode, pairScope: "all" })}
              className="mt-4 rounded-md border border-white/15 px-3 py-2 text-xs text-white/75 hover:bg-white/5 cursor-pointer">
              Clear filters
            </button>
          </div>
          </>
        ) : (
          <NewsTable items={data.items} now={now} categoryLabel={categoryLabel} />
        )}
      </div>
    </main>
  );
}
