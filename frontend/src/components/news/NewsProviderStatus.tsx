import type { NewsStatus } from "../../types/news";
import { NewsTime } from "./NewsCards";

export function NewsProviderStatus({ data, isError, now }: { data?: NewsStatus; isError: boolean; now: number }) {
  return (
    <details className="relative shrink-0 text-xs text-white/50">
      <summary className="cursor-pointer rounded-md border border-white/15 px-3 py-2 hover:bg-white/5">
        {isError ? "Last known provider status" : "Provider status"}
        {data && <span className="hidden sm:inline"> · Checked <NewsTime value={data.checkedAt} now={now} /></span>}
      </summary>
      <div className="absolute right-0 z-20 mt-2 w-96 max-w-[calc(100vw-3rem)] rounded-lg border border-white/15 bg-[#111] p-4 space-y-3 shadow-xl">
      {isError && (
        <p role="status" className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-amber-200">
          Provider status is unavailable. Current provider health is unknown{data ? "; statuses below are last known" : ""}.
        </p>
      )}
      {data?.ai.status === "unavailable" && (
        <p role="status" className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-white/60">
          {isError ? "Last known AI status: unavailable." : "New Claude insights are currently unavailable."} {data.ai.message} Source reports and previously validated insights remain available.
        </p>
      )}
      {data && (
        <div className="text-white/50">
          {data.sources.length === 0 ? <p className="mt-2">No news providers configured.</p> : (
            <ul className="space-y-3">
              {data.sources.map((source) => (
                <li key={source.id}>
                  <span className={source.status === "healthy" ? "text-emerald-300" : "text-amber-200"}>{source.name}: {source.status}</span>
                  {source.message && <p className="mt-1 break-words">{source.message}</p>}
                  <p className="mt-1">Last collection: <NewsTime value={source.lastSuccessfulRefreshAt} now={now} /></p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {!data && !isError && <p role="status">Loading provider status…</p>}
      </div>
    </details>
  );
}
