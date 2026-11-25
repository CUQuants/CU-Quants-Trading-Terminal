import { useEffect, useState } from "react";
import type { KillSwitchStatus } from "../types/risk";
import { useRiskStatus } from "../hooks/useRiskStatus";
import { formatNum } from "../utils/format";
import { StatCard } from "./ui/StatCard";

/** The RMU's default kill_switch.max_nav_age_s: past it, risk-adding orders are denied. */
const NAV_MAX_AGE_S = 30;

function num(s: string | null | undefined, decimals = 2): string {
  if (s == null || s === "") return "—";
  const n = Number(s);
  return Number.isFinite(n) ? formatNum(n, decimals) : s;
}

function signed(s: string | null | undefined, decimals = 2): string {
  if (s == null || s === "") return "—";
  const n = Number(s);
  if (!Number.isFinite(n)) return s;
  const out = formatNum(n, decimals);
  return n > 0 ? `+${out}` : out;
}

function time(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function ageSeconds(iso: string | null | undefined, now: number): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return isNaN(t) ? null : Math.max(0, (now - t) / 1000);
}

function ago(s: number | null): string {
  if (s == null) return "";
  if (s < 90) return `${Math.round(s)}s ago`;
  if (s < 5400) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}

const BASELINE_SOURCE: Record<string, string> = {
  config: "set in config",
  stored: "restored after restart",
  first_sample: "first NAV sample",
  rebase: "reset on clear",
};

function StateBanner({ ks }: { ks: KillSwitchStatus }) {
  if (!ks.enabled) {
    return (
      <div className="mx-6 mt-4 rounded-lg border border-white/10 bg-white/[0.03] px-5 py-4">
        <div className="text-lg font-semibold text-white/60">Kill switch disabled</div>
        <div className="text-xs text-white/40 mt-1">
          The RMU is not enforcing a PnL loss limit (kill_switch.enabled is off).
        </div>
      </div>
    );
  }
  if (ks.tripped) {
    return (
      <div className="mx-6 mt-4 rounded-lg border border-red-400/30 bg-red-500/[0.08] px-5 py-4">
        <div className="text-lg font-semibold text-red-400">Kill switch TRIPPED: risk-adding orders are blocked</div>
        {ks.trip_reason && <div className="text-sm text-red-200/80 mt-1">{ks.trip_reason}</div>}
        <div className="text-xs text-white/40 mt-2">
          Cancels and reducing orders still go through. It stays tripped until an operator clears it on the RMU,
          even if PnL recovers.
        </div>
      </div>
    );
  }
  return (
    <div className="mx-6 mt-4 rounded-lg border border-emerald-400/20 bg-emerald-400/[0.06] px-5 py-4">
      <div className="text-lg font-semibold text-emerald-400">Kill switch armed</div>
      <div className="text-xs text-white/40 mt-1">
        Trading is allowed. It trips when PnL since the baseline falls to −{num(ks.threshold)}.
      </div>
    </div>
  );
}

/** How much of the loss limit is used: 0% at or above the baseline, 100% at the trip line. */
function LossMeter({ ks }: { ks: KillSwitchStatus }) {
  const pnl = Number(ks.pnl);
  const threshold = Number(ks.threshold);
  if (ks.pnl == null || ks.threshold == null || !Number.isFinite(pnl) || !(threshold > 0)) return null;
  const used = Math.min(1, Math.max(0, -pnl / threshold));
  const color = used >= 1 ? "bg-red-500" : used >= 0.75 ? "bg-red-400" : used >= 0.5 ? "bg-amber-400" : "bg-emerald-400";
  return (
    <div className="mx-6 mb-2">
      <div className="flex justify-between text-[10px] uppercase tracking-widest text-white/30 mb-1">
        <span>Loss limit used</span>
        <span className="tabular-nums">{formatNum(used * 100, 1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
        <div className={`h-full ${color} transition-all`} style={{ width: `${used * 100}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-white/30 mt-1 tabular-nums">
        <span>0 (baseline)</span>
        <span>−{num(ks.threshold)} (trips)</span>
      </div>
    </div>
  );
}

function Warnings({ ks, navAge }: { ks: KillSwitchStatus; navAge: number | null }) {
  const items: string[] = [];
  if (ks.enabled && !ks.trip_persisted) {
    items.push("The trip is held in memory but couldn't be saved to the database yet; the RMU keeps retrying.");
  }
  if (ks.enabled && ks.baseline_nav == null) {
    items.push("No baseline yet: the RMU uses the first complete NAV sample. Until then, risk-adding orders are blocked.");
  } else if (ks.enabled && !ks.baseline_persisted) {
    items.push("The baseline isn't saved yet: a restart now would start a new PnL window.");
  }
  if (ks.enabled && ks.nav == null) {
    items.push("No complete NAV sample yet: risk-adding orders are blocked until there is one.");
  } else if (ks.enabled && navAge != null && navAge > NAV_MAX_AGE_S) {
    items.push(
      `NAV is ${Math.round(navAge)}s old. Past the RMU's max age (${NAV_MAX_AGE_S}s by default) risk-adding orders are blocked.`,
    );
  }
  if (items.length === 0) return null;
  return (
    <div className="mx-6 mb-3 rounded-md border border-amber-400/20 bg-amber-400/[0.06] px-4 py-2 text-xs text-amber-200/90 space-y-1">
      {items.map((m) => <div key={m}>⚠ {m}</div>)}
    </div>
  );
}

export function RiskView() {
  const [auto, setAuto] = useState(true);
  const [showRaw, setShowRaw] = useState(false);
  const risk = useRiskStatus(auto ? 5_000 : false);
  const ks = risk.data?.kill_switch;

  // Re-render every second so the NAV age keeps counting between polls.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(id);
  }, []);
  const navAge = ageSeconds(ks?.nav_as_of, now);

  const headroom = ks && ks.pnl != null && ks.threshold != null
    ? String(Number(ks.pnl) + Number(ks.threshold))
    : null;

  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-4 px-6 py-3 border-b border-white/10 bg-white/[0.02] text-xs">
        <span className="text-white/50">RMU risk status · PnL kill switch</span>
        {risk.isFetching && (
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
          onClick={() => risk.refetch()}
          className="text-white/40 hover:text-white/70 transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          Refresh
        </button>
      </div>

      {risk.isLoading ? (
        <div className="flex items-center justify-center py-24 text-white/30">
          <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mr-3" />
          Loading risk status…
        </div>
      ) : risk.error && !ks ? (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-red-400/80 text-sm text-center px-6">
          <p>Failed to load risk status</p>
          <p className="text-white/40 text-xs max-w-xl">{(risk.error as Error).message}</p>
        </div>
      ) : ks ? (
        <>
          {risk.error && (
            <div className="mx-6 mt-3 rounded-md border border-red-400/20 bg-red-400/[0.06] px-4 py-2 text-xs text-red-300/90">
              Last refresh failed, showing the previous status: {(risk.error as Error).message}
            </div>
          )}

          <StateBanner ks={ks} />

          {ks.enabled && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 px-6 py-4">
                <StatCard label="PnL since baseline" value={signed(ks.pnl)} />
                <StatCard label="Trips at" value={ks.threshold != null ? `−${num(ks.threshold)}` : "—"} />
                <StatCard label="Headroom to trip" value={num(headroom)} />
                <StatCard label={`NAV${navAge != null ? ` · ${ago(navAge)}` : ""}`} value={num(ks.nav)} />
              </div>

              <LossMeter ks={ks} />
              <Warnings ks={ks} navAge={navAge} />

              <div className="px-6 py-2 text-xs text-white/40 space-y-1">
                <div>
                  Baseline NAV <span className="text-white/70 tabular-nums">{num(ks.baseline_nav)}</span>
                  {" "}since <span className="text-white/70">{time(ks.baseline_ts)}</span>
                  {ks.baseline_source && <> ({BASELINE_SOURCE[ks.baseline_source] ?? ks.baseline_source})</>}
                </div>
                <div>
                  PnL = NAV now − baseline NAV − deposits/withdrawals since the baseline. Values are in the RMU&apos;s
                  valuation currency.
                </div>
                <div>NAV as of {time(ks.nav_as_of)}</div>
              </div>
            </>
          )}

          {showRaw && (
            <pre className="mx-6 my-4 p-4 rounded-md bg-black/40 border border-white/10 text-[11px] text-white/60 overflow-auto">
              {JSON.stringify(risk.data, null, 2)}
            </pre>
          )}
        </>
      ) : null}
    </div>
  );
}
