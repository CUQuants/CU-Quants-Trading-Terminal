import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { BotFileKind, BotMarket } from "../types/bots";
import { useBotStatus } from "../hooks/useBots";
import { startBot, stopBot } from "../api/bots";
import { BotFileEditor } from "./BotFileEditor";
import { LaunchMarketModal } from "./LaunchMarketModal";

/**
 * Bot Monitor — xlrts's botmon in the terminal. Live status of every speedbyte
 * market on the Proxy box, Start / Stop, Config / Subaccount editors and
 * Launch Market. Everything goes through the gateway's /v1/bots with the
 * signed-in trader's own credential; what they may do is their bot_role.
 */

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** Where Start would type: its own session / CUQuants window. Older gateways
 *  send no `home`; then only an own session counts, as in xlrts. */
function homeOf(r: BotMarket): string {
  if (r.home !== undefined) return r.home;
  return r.session ? r.market : "";
}

function statusOf(r: BotMarket): { label: string; cls: string; dot: string } {
  if (r.instances > 1) {
    return { label: `${r.instances} running!`, cls: "bg-red-500/20 text-red-300", dot: "text-red-400" };
  }
  if (r.running) return { label: "Running", cls: "bg-emerald-500/10 text-emerald-400", dot: "text-emerald-400" };
  if (homeOf(r)) return { label: "Stopped", cls: "bg-red-500/10 text-red-400", dot: "text-red-400" };
  return { label: "No window", cls: "bg-white/[0.04] text-white/40", dot: "text-white/30" };
}

interface RowNote {
  text: string;
  error: boolean;
}

export function BotMonitorView() {
  const queryClient = useQueryClient();
  const [auto, setAuto] = useState(true);
  const status = useBotStatus(auto ? 3_000 : false);
  const data = status.data;
  const rows = data?.markets ?? [];

  const [notes, setNotes] = useState<Record<string, RowNote>>({});
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const [busy, setBusy] = useState<Set<string>>(new Set());
  const [bulk, setBulk] = useState<"" | "start" | "stop">("");
  const [editing, setEditing] = useState<{ market: string; kind: BotFileKind } | null>(null);
  const [launching, setLaunching] = useState(false);

  /** A transient line in the row's output cell, like xlrts's _set_output. */
  const note = useCallback((market: string, text: string, error = false) => {
    clearTimeout(timers.current[market]);
    setNotes((n) => ({ ...n, [market]: { text, error } }));
    timers.current[market] = setTimeout(() => {
      setNotes((n) => {
        const rest = { ...n };
        delete rest[market];
        return rest;
      });
    }, error ? 12_000 : 4_000);
  }, []);

  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ["bots"] }),
    [queryClient],
  );

  const setRowBusy = (market: string, on: boolean) =>
    setBusy((b) => {
      const next = new Set(b);
      if (on) next.add(market);
      else next.delete(market);
      return next;
    });

  /** "" on success, else the gateway's reason. */
  async function send(action: "start" | "stop", market: string): Promise<string> {
    setRowBusy(market, true);
    note(market, action === "start" ? `Starting ${market}…` : "Stopping…");
    try {
      await (action === "start" ? startBot(market) : stopBot(market));
      return "";
    } catch (e) {
      const msg = errText(e);
      note(market, `Error: ${msg}`, true);
      return msg;
    } finally {
      setRowBusy(market, false);
    }
  }

  async function startOne(market: string) {
    await send("start", market);
    await sleep(1_500);
    await refresh();
  }

  async function stopOne(market: string) {
    await send("stop", market);
    await sleep(800);
    await refresh();
  }

  async function startAll() {
    // Only markets that already have a tmux home, as in xlrts: a config with
    // nowhere to run is a market nobody set up yet; starting it is per-row.
    const targets = rows.filter((r) => homeOf(r) && !r.running).map((r) => r.market);
    if (targets.length === 0) {
      toast("Nothing to start: every market with a window is already running.");
      return;
    }
    if (!window.confirm(`Start ${targets.length} bot(s)?\n\n${targets.join(", ")}`)) return;
    setBulk("start");
    try {
      for (const m of targets) {
        await send("start", m);
        await sleep(300);
      }
      await sleep(1_500);
      await refresh();
    } finally {
      setBulk("");
    }
  }

  async function stopAll() {
    const targets = rows.filter((r) => r.running).map((r) => r.market);
    if (targets.length === 0) {
      toast("No bots are running.");
      return;
    }
    if (!window.confirm(`Stop ${targets.length} running bot(s)?\n\n${targets.join(", ")}`)) return;
    setBulk("stop");
    try {
      for (const m of targets) {
        await send("stop", m);
        await sleep(200);
      }
      await sleep(1_000);
      await refresh();
    } finally {
      setBulk("");
    }
  }

  const nRunning = rows.filter((r) => r.running).length;
  const warning =
    data?.error || (data && data.tmux_server === false ? "no tmux server is running on the box" : "");

  const th = "px-3 py-2 text-[10px] font-medium uppercase tracking-widest text-white/30";
  const btn =
    "cursor-pointer rounded-md px-3 py-1 text-xs font-medium border transition-colors disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-white/10 bg-white/[0.02] text-xs">
        <span className="text-white/50">
          {data ? (
            <>
              <span className="text-white/80 font-medium">{nRunning}/{rows.length}</span> running
              <span className="text-white/30 font-mono ml-3">{data.root}</span>
            </>
          ) : (
            "speedbyte bots"
          )}
        </span>
        {status.isFetching && (
          <span className="w-3 h-3 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
        )}
        <div className="flex-1" />
        <label className="flex items-center gap-2 text-white/50 cursor-pointer select-none">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          Auto-refresh (3s)
        </label>
        <button
          onClick={() => setLaunching(true)}
          className={`${btn} border-sky-400/30 text-sky-300 bg-sky-400/[0.06] hover:bg-sky-400/[0.12]`}
        >
          ＋ Launch Market
        </button>
        <button
          onClick={() => void stopAll()}
          disabled={!!bulk || !data}
          className={`${btn} border-red-400/30 text-red-300 bg-red-400/[0.06] hover:bg-red-400/[0.12]`}
        >
          {bulk === "stop" ? "Stopping…" : "■■ Stop All"}
        </button>
        <button
          onClick={() => void startAll()}
          disabled={!!bulk || !data}
          className={`${btn} border-emerald-400/30 text-emerald-300 bg-emerald-400/[0.06] hover:bg-emerald-400/[0.12]`}
        >
          {bulk === "start" ? "Starting…" : "▶▶ Start All"}
        </button>
        <button
          onClick={() => void status.refetch()}
          className={`${btn} border-white/10 text-white/40 hover:text-white/70`}
        >
          Refresh
        </button>
      </div>

      {status.isLoading ? (
        <div className="flex items-center justify-center py-24 text-white/30">
          <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mr-3" />
          Connecting to the bot box…
        </div>
      ) : status.error && !data ? (
        <div className="flex flex-col items-center justify-center py-24 gap-2 text-red-400/80 text-sm text-center px-6">
          <p>Could not reach the bots</p>
          <p className="text-white/40 text-xs max-w-xl">{errText(status.error)}</p>
        </div>
      ) : (
        <>
          {status.error && (
            <div className="mx-6 mt-3 rounded-md border border-red-400/20 bg-red-400/[0.06] px-4 py-2 text-xs text-red-300/90">
              Last refresh failed, showing the previous status: {errText(status.error)}
            </div>
          )}
          {warning && (
            <div className="mx-6 mt-3 rounded-md border border-amber-400/20 bg-amber-400/[0.06] px-4 py-2 text-xs text-amber-200/90">
              ⚠ {warning}
            </div>
          )}

          <div className="px-6 py-4 overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-left">
                  <th className={`${th} w-6`} />
                  <th className={`${th} w-8 text-right`}>#</th>
                  <th className={th}>Market</th>
                  <th className={th}>Status</th>
                  <th className={th}>Where</th>
                  <th className={`${th} w-full`}>Last output</th>
                  <th className={th} colSpan={4} />
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={10} className="py-16 text-center text-white/30">
                      No markets: the box has no configs in data/configs.
                    </td>
                  </tr>
                )}
                {rows.map((r, i) => {
                  const s = statusOf(r);
                  const n = notes[r.market];
                  const rowBusy = busy.has(r.market) || !!bulk;
                  const where = r.running ? r.location : homeOf(r);
                  return (
                    <tr key={r.market} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                      <td className={`px-3 py-2 text-center ${s.dot}`}>{r.running ? "●" : "○"}</td>
                      <td className="px-3 py-2 text-right text-white/30 tabular-nums">{i + 1}</td>
                      <td className="px-3 py-2 font-semibold whitespace-nowrap">{r.market}</td>
                      <td className="px-3 py-2">
                        <span className={`inline-block rounded px-2 py-0.5 text-xs whitespace-nowrap ${s.cls}`}>
                          {s.label}
                        </span>
                      </td>
                      <td
                        className="px-3 py-2 font-mono text-xs text-white/50 whitespace-nowrap"
                        title={where ? undefined : "Start will create a window for it in CUQuants"}
                      >
                        {where || "—"}
                      </td>
                      <td
                        className={`px-3 py-2 font-mono text-xs max-w-0 truncate ${
                          n ? (n.error ? "text-red-400" : "text-sky-300") : "text-white/50"
                        }`}
                        title={n?.text ?? r.last}
                      >
                        {n?.text ?? r.last}
                      </td>
                      <td className="px-1 py-1.5">
                        <button
                          onClick={() => void startOne(r.market)}
                          disabled={rowBusy || r.running}
                          className={`${btn} whitespace-nowrap border-emerald-400/20 text-emerald-300 hover:bg-emerald-400/[0.1]`}
                        >
                          ▶ Start
                        </button>
                      </td>
                      <td className="px-1 py-1.5">
                        <button
                          onClick={() => void stopOne(r.market)}
                          disabled={rowBusy || !r.running}
                          className={`${btn} whitespace-nowrap border-red-400/20 text-red-300 hover:bg-red-400/[0.1]`}
                        >
                          ■ Stop
                        </button>
                      </td>
                      <td className="px-1 py-1.5">
                        <button
                          onClick={() => setEditing({ market: r.market, kind: "config" })}
                          className={`${btn} whitespace-nowrap border-sky-400/20 text-sky-300 hover:bg-sky-400/[0.1]`}
                        >
                          ⚙ Config
                        </button>
                      </td>
                      <td className="px-1 py-1.5">
                        <button
                          onClick={() => setEditing({ market: r.market, kind: "subaccount" })}
                          className={`${btn} whitespace-nowrap border-sky-400/20 text-sky-300 hover:bg-sky-400/[0.1]`}
                        >
                          ⚙ Subacct
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {editing && (
        <BotFileEditor
          market={editing.market}
          kind={editing.kind}
          root={data?.root ?? ""}
          onClose={() => setEditing(null)}
        />
      )}
      {launching && (
        <LaunchMarketModal
          existing={rows.map((r) => r.market)}
          root={data?.root ?? ""}
          onClose={() => setLaunching(false)}
          onLaunched={() => void refresh()}
        />
      )}
    </div>
  );
}
