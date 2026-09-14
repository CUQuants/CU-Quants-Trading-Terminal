import { useState } from "react";
import type { LogFilters } from "../types/reporting";
import { ApiError } from "../api/orders";
import { useLogHealth } from "../hooks/useLogHealth";
import { useUnresolvedOrders } from "../hooks/useUnresolvedOrders";
import { useAuthFailures } from "../hooks/useAuthFailures";
import { useLogs } from "../hooks/useLogs";
import { StatCard } from "./ui/StatCard";
import { FilterToggle } from "./ui/FilterToggle";
import { ReportingLogsTable } from "./ReportingLogsTable";

const RESPONSE_STATUS_OPTIONS = [
  { value: "" as const, label: "All" },
  { value: "success" as const, label: "Success" },
  { value: "error" as const, label: "Error" },
];

const EXCHANGE_OPTIONS = [
  { value: "" as const, label: "All" },
  { value: "okx" as const, label: "OKX" },
  { value: "kraken" as const, label: "Kraken" },
];

export function ReportingView() {
  const [filters, setFilters] = useState<LogFilters>({ limit: 50 });
  const [cursorStack, setCursorStack] = useState<string[]>([]);

  const health = useLogHealth();
  const unresolved = useUnresolvedOrders();
  const authFailures = useAuthFailures();
  const logs = useLogs(filters);

  const notConfigured =
    health.error instanceof ApiError && health.error.status === 503;

  function updateFilter(patch: Partial<LogFilters>) {
    setCursorStack([]);
    setFilters((f) => ({ ...f, ...patch, cursor: undefined }));
  }

  function loadMore() {
    if (!logs.data?.next_cursor) return;
    setCursorStack((s) => [...s, filters.cursor ?? ""]);
    setFilters((f) => ({ ...f, cursor: logs.data!.next_cursor! }));
  }

  function loadPrevious() {
    if (cursorStack.length === 0) return;
    const prev = cursorStack[cursorStack.length - 1];
    setCursorStack((s) => s.slice(0, -1));
    setFilters((f) => ({ ...f, cursor: prev || undefined }));
  }

  if (notConfigured) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-white/30 gap-2">
        <p className="text-lg">Reporting API not configured</p>
        <p className="text-sm">
          Set <code className="text-white/50">CUQ_REPORTING_URL</code> in the
          backend's environment to enable the audit log.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Health stat cards */}
      <div className="grid grid-cols-4 gap-3 px-6 py-4">
        <StatCard
          label="Months of Runway"
          value={health.data ? String(health.data.months_of_runway) : "—"}
        />
        <StatCard
          label="Rows (24h)"
          value={health.data ? String(health.data.rows_last_24h) : "—"}
        />
        <StatCard
          label="Unprotected Partitions"
          value={health.data ? String(health.data.unprotected_partitions) : "—"}
        />
        <StatCard
          label="Max Clock Skew"
          value={
            health.data?.max_clock_skew_sec != null
              ? `${health.data.max_clock_skew_sec.toFixed(2)}s`
              : "—"
          }
        />
      </div>

      {/* Unresolved orders banner */}
      {unresolved.data && unresolved.data.length > 0 && (
        <div className="mx-6 mb-4 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
          <span className="font-semibold">
            {unresolved.data.length} unresolved order
            {unresolved.data.length === 1 ? "" : "s"}
          </span>{" "}
          — forwarded to an exchange with no recorded outcome:{" "}
          {unresolved.data
            .slice(0, 5)
            .map((o) => `${o.exchange ?? "?"}/${o.action}`)
            .join(", ")}
          {unresolved.data.length > 5 ? ", …" : ""}
        </div>
      )}

      {/* Auth failures */}
      {authFailures.data && authFailures.data.length > 0 && (
        <details className="mx-6 mb-4 px-4 py-3 rounded-lg bg-red-500/5 border border-red-500/15 text-xs">
          <summary className="cursor-pointer text-red-300 font-semibold">
            Auth failures (7d): {authFailures.data.length}
          </summary>
          <table className="w-full mt-2 text-white/60">
            <tbody>
              {authFailures.data.map((f, i) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="py-1 pr-4">{f.api_key_id || "—"}</td>
                  <td className="py-1 pr-4">{f.source_ip || "—"}</td>
                  <td className="py-1 pr-4">{f.failures} failures</td>
                  <td className="py-1">{f.latest}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-4 px-6 py-3 border-y border-white/10 bg-white/[0.02] flex-wrap">
        <FilterToggle
          value={filters.exchange ?? ""}
          onChange={(v) => updateFilter({ exchange: v || undefined })}
          options={EXCHANGE_OPTIONS}
        />
        <FilterToggle
          value={filters.response_status ?? ""}
          onChange={(v) => updateFilter({ response_status: v || undefined })}
          options={RESPONSE_STATUS_OPTIONS}
        />
        <input
          placeholder="Operator ID"
          value={filters.operator_id ?? ""}
          onChange={(e) => updateFilter({ operator_id: e.target.value || undefined })}
          className="bg-transparent border border-white/10 rounded-md px-2.5 py-1 text-xs text-white/80 outline-none focus:border-white/30 w-32"
        />
        <input
          placeholder="Action"
          value={filters.action ?? ""}
          onChange={(e) => updateFilter({ action: e.target.value || undefined })}
          className="bg-transparent border border-white/10 rounded-md px-2.5 py-1 text-xs text-white/80 outline-none focus:border-white/30 w-32"
        />
        <input
          placeholder="Request ID"
          value={filters.request_id ?? ""}
          onChange={(e) => updateFilter({ request_id: e.target.value || undefined })}
          className="bg-transparent border border-white/10 rounded-md px-2.5 py-1 text-xs text-white/80 outline-none focus:border-white/30 w-40"
        />

        <div className="flex-1" />

        <button
          onClick={() => {
            health.refetch();
            unresolved.refetch();
            authFailures.refetch();
            logs.refetch();
          }}
          className="text-xs text-white/40 hover:text-white/70 transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto px-6 py-2">
        {logs.isLoading ? (
          <div className="flex items-center justify-center py-24 text-white/30">
            <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mr-3" />
            Loading logs…
          </div>
        ) : logs.error ? (
          <div className="flex items-center justify-center py-24 text-red-400/80">
            Failed to load logs: {(logs.error as Error).message}
          </div>
        ) : (
          <ReportingLogsTable logs={logs.data?.logs ?? []} />
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-end gap-2 px-6 py-3">
        <button
          onClick={loadPrevious}
          disabled={cursorStack.length === 0}
          className="text-xs text-white/40 hover:text-white/70 disabled:opacity-30 disabled:cursor-not-allowed transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          Previous
        </button>
        <button
          onClick={loadMore}
          disabled={!logs.data?.next_cursor}
          className="text-xs text-white/40 hover:text-white/70 disabled:opacity-30 disabled:cursor-not-allowed transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          Load more
        </button>
      </div>
    </div>
  );
}
