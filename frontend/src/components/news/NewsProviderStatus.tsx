import type { NewsStatus } from "../../types/news";
import { NewsTime } from "./NewsCards";

export function NewsProviderStatus({ data, isError, now }: { data?: NewsStatus; isError: boolean; now: number }) {
  const failures = data?.sources.filter((source) => source.status !== "healthy") ?? [];
  return (
    <div className="space-y-3 text-xs">
      {isError && (
        <p role="status" className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-amber-200">
          Provider status is unavailable. Current provider health is unknown{data ? "; statuses below are last known" : ""}.
        </p>
      )}
      {failures.length > 0 && (
        <div role="status" className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-amber-200">
          <p>{isError ? "Last known provider issues" : "Some news providers are having problems"}. Available reports remain visible.</p>
          <ul className="mt-2 space-y-1">
            {failures.map((source) => (
              <li key={source.id}>
                {source.name}: {source.message || source.status} · Last successful collection: <NewsTime value={source.lastSuccessfulRefreshAt} now={now} />
              </li>
            ))}
          </ul>
        </div>
      )}
      {data?.ai.status === "unavailable" && (
        <p role="status" className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-white/60">
          {isError ? "Last known AI status: unavailable." : "New Claude insights are currently unavailable."} {data.ai.message} Source reports and previously validated insights remain available.
        </p>
      )}
      {data && (
        <details className="text-white/50">
          <summary className="cursor-pointer">{isError ? "Last known provider status" : "Provider status"} · Checked <NewsTime value={data.checkedAt} now={now} /></summary>
          {data.sources.length === 0 ? <p className="mt-2">No news providers configured.</p> : (
            <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
              {data.sources.map((source) => (
                <li key={source.id}>
                  <span className={source.status === "healthy" ? "text-emerald-300" : "text-amber-200"}>{source.name}: {source.status}</span>
                  <span> · Last collection: <NewsTime value={source.lastSuccessfulRefreshAt} now={now} /></span>
                </li>
              ))}
            </ul>
          )}
        </details>
      )}
    </div>
  );
}
