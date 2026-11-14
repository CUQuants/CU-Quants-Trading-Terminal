import { useState } from "react";
import type { PnlGroup, PnlReport } from "../types/pnl";
import { usePnl } from "../hooks/usePnl";
import { formatNum } from "../utils/format";
import { StatCard } from "./ui/StatCard";

/** RMU decimals arrive as strings; null means "not computable right now". */
function num(s: string | null | undefined, decimals = 4): string {
  if (s == null || s === "") return "—";
  const n = Number(s);
  return Number.isFinite(n) ? formatNum(n, decimals) : s;
}

function signed(s: string | null | undefined, decimals = 4): string {
  if (s == null || s === "") return "—";
  const n = Number(s);
  if (!Number.isFinite(n)) return s;
  const out = formatNum(n, decimals);
  return n > 0 ? `+${out}` : out;
}

function pnlColor(s: string | null | undefined): string {
  const n = Number(s);
  if (s == null || !Number.isFinite(n) || Math.abs(n) < 1e-9) return "text-white/70";
  return n > 0 ? "text-emerald-400" : "text-red-400";
}

function time(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function GroupStatus({ g }: { g: PnlGroup }) {
  if (!g.opened) return <span className="text-amber-400">not opened</span>;
  if (g.feed_down) return <span className="text-red-400" title={g.feed_down}>feed down</span>;
  if (g.mark_error) return <span className="text-red-400" title={g.mark_error}>no mark</span>;
  if (g.mark_age_s != null && g.mark_age_s > 30) {
    return <span className="text-amber-400">mark {Math.round(g.mark_age_s)}s old</span>;
  }
  return <span className="text-emerald-400/80">live</span>;
}

function Warnings({ report }: { report: PnlReport }) {
  const items: string[] = [];
  if (!report.pair_pnl.running) {
    items.push(`Pair PnL is not running on the RMU${report.pair_pnl.error ? `: ${report.pair_pnl.error}` : ""}`);
  } else if (report.pair_pnl.error) {
    items.push(`RMU reports: ${report.pair_pnl.error}`);
  }
  if (report.pair_pnl.untracked.length > 0) {
    items.push(`Traded but not tracked (no PnL): ${report.pair_pnl.untracked.join(", ")}`);
  }
  if (report.total && !report.total.complete) {
    items.push(`Total is incomplete${report.total.missing.length ? `, missing: ${report.total.missing.join(", ")}` : ""}`);
  }
  if (report.portfolio && report.portfolio.unpriced.length > 0) {
    items.push(`Portfolio NAV has unpriced assets: ${report.portfolio.unpriced.join(", ")}`);
  }
  for (const g of report.groups) {
    const fees = Object.entries(g.unconverted_fees ?? {});
    if (fees.length > 0) {
      items.push(`${g.market}: fees not in PnL (unconverted): ${fees.map(([c, a]) => `${a} ${c}`).join(", ")}`);
    }
  }
  if (items.length === 0) return null;
  return (
    <div className="mx-6 mb-3 rounded-md border border-amber-400/20 bg-amber-400/[0.06] px-4 py-2 text-xs text-amber-200/90 space-y-1">
      {items.map((m) => <div key={m}>⚠ {m}</div>)}
    </div>
  );
}

export function PnlView() {
  const [auto, setAuto] = useState(true);
  const [showRaw, setShowRaw] = useState(false);
  const pnl = usePnl(auto ? 5_000 : false);
  const report = pnl.data;

  const th = "px-3 py-2 text-[10px] font-medium uppercase tracking-widest text-white/30";
  const td = "px-3 py-2 tabular-nums";

  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-4 px-6 py-3 border-b border-white/10 bg-white/[0.02] text-xs">
        <span className="text-white/50">
          RMU PnL report{report ? ` · as of ${time(report.as_of)}` : ""}
        </span>
        {pnl.isFetching && (
          <span className="w-3 h-3 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
        )}
        <div className="flex-1" />
        <label className="flex items-center gap-2 text-white/50 cursor-pointer select-none">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          Auto-refresh (5s)
        </label>
        <button
          onClick={() => setShowRaw((v) => !v)}
          className="text-white/40 hover:text-white/70 transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          {showRaw ? "Hide" : "Show"} raw JSON
        </button>
        <button
          onClick={() => pnl.refetch()}
          className="text-white/40 hover:text-white/70 transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          Refresh
        </button>
      </div>

      {pnl.isLoading ? (
        <div className="flex items-center justify-center py-24 text-white/30">
          <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mr-3" />
          Loading PnL…
        </div>
      ) : pnl.error && !report ? (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-red-400/80 text-sm text-center px-6">
          <p>Failed to load PnL</p>
          <p className="text-white/40 text-xs max-w-xl">{(pnl.error as Error).message}</p>
        </div>
      ) : report ? (
        <>
          {pnl.error && (
            <div className="mx-6 mt-3 rounded-md border border-red-400/20 bg-red-400/[0.06] px-4 py-2 text-xs text-red-300/90">
              Last refresh failed, showing the previous report: {(pnl.error as Error).message}
            </div>
          )}

          {/* Totals */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 px-6 py-4">
            <StatCard
              label={`Total PnL (${report.total?.ccy ?? "—"})${report.total && !report.total.complete ? " · incomplete" : ""}`}
              value={signed(report.total?.pnl, 4)}
            />
            {Object.entries(report.totals).map(([ccy, t]) => (
              <StatCard
                key={ccy}
                label={`${ccy}: realized / unrealized / fees`}
                value={`${signed(t.realized, 2)} / ${signed(t.unrealized, 2)} / ${num(t.fees, 2)}`}
              />
            ))}
            <StatCard
              label={`Portfolio NAV (${report.portfolio?.quote_ccy ?? "—"})${report.portfolio && !report.portfolio.complete ? " · incomplete" : ""}`}
              value={num(report.portfolio?.nav, 2)}
            />
          </div>

          <Warnings report={report} />

          {/* Per-pair table */}
          <div className="flex-1 overflow-auto px-6 pb-4">
            {report.groups.length === 0 ? (
              <div className="py-16 text-center text-white/30 text-sm">
                No pairs configured on the RMU (pair_pnl.pairs is empty).
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="border-b border-white/10 text-left">
                  <tr>
                    <th className={th}>Pair</th>
                    <th className={`${th} text-right`}>Position</th>
                    <th className={`${th} text-right`}>Avg cost</th>
                    <th className={`${th} text-right`}>Bid / Ask</th>
                    <th className={`${th} text-right`}>Mark</th>
                    <th className={`${th} text-right`}>Realized</th>
                    <th className={`${th} text-right`}>Unrealized</th>
                    <th className={`${th} text-right`}>Fees</th>
                    <th className={`${th} text-right`}>PnL</th>
                    <th className={`${th} text-right`}>Fills</th>
                    <th className={th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {report.groups.map((g) => (
                    <tr key={g.key} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="px-3 py-2">
                        <div className="font-medium text-white/90">{g.market}</div>
                        <div className="text-[10px] text-white/30">
                          {g.venue} · {g.quote_ccy} · since {time(g.opened_at)}
                        </div>
                      </td>
                      <td className={`${td} text-right`}>{num(g.position, 4)} <span className="text-white/30">{g.base}</span></td>
                      <td className={`${td} text-right`}>{num(g.avg_cost, 4)}</td>
                      <td className={`${td} text-right text-white/50`}>{num(g.bid, 4)} / {num(g.ask, 4)}</td>
                      <td className={`${td} text-right`}>
                        {num(g.mark, 4)}
                        {g.mark_age_s != null && <span className="text-white/30"> · {g.mark_age_s.toFixed(1)}s</span>}
                      </td>
                      <td className={`${td} text-right ${pnlColor(g.realized)}`}>{signed(g.realized)}</td>
                      <td className={`${td} text-right ${pnlColor(g.unrealized)}`}>{signed(g.unrealized)}</td>
                      <td className={`${td} text-right text-white/60`}>{num(g.fees)}</td>
                      <td className={`${td} text-right font-semibold ${pnlColor(g.pnl)}`}>
                        {signed(g.pnl)} <span className="text-white/30 font-normal">{g.quote_ccy}</span>
                      </td>
                      <td className={`${td} text-right text-white/60`}>{g.fills}</td>
                      <td className="px-3 py-2"><GroupStatus g={g} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <p className="mt-3 text-[10px] text-white/30">
              Average-cost PnL from the RMU&apos;s fill log, marked to each market&apos;s mid. PnL = realized + unrealized − fees,
              in the pair&apos;s quote currency, counted from when each pair opened. Fills before that are stored, not counted.
            </p>

            {showRaw && (
              <pre className="mt-4 max-h-[50vh] overflow-auto rounded-md border border-white/10 bg-white/[0.02] p-3 text-[11px] text-white/70">
                {JSON.stringify(report, null, 2)}
              </pre>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
