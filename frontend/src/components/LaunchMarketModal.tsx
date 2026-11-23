import { useState } from "react";
import toast from "react-hot-toast";
import type { ExchangeLaunchSettings, LaunchMarketRequest } from "../types/bots";
import { launchMarket } from "../api/bots";

interface Props {
  existing: string[];
  root: string;
  onClose: () => void;
  onLaunched: () => void;
}

const MARKET_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;

type Venue = "okx" | "kraken" | "gemini";

// xlrts's Launch Market defaults.
const DEFAULTS: Record<Venue, ExchangeLaunchSettings> = {
  okx: { enabled: true, trading_pair: "", reference_pair: "", minimum_spread: "2.00", center_buffer: "0.00", tick_level: "0.0001" },
  kraken: { enabled: false, trading_pair: "", reference_pair: "", minimum_spread: "99.00", center_buffer: "0.00", tick_level: "0.0001" },
  gemini: { enabled: false, trading_pair: "", reference_pair: "", minimum_spread: "40.00", center_buffer: "1.00", tick_level: "0.0001" },
};

const LABELS: Record<Venue, string> = { okx: "OKX", kraken: "Kraken", gemini: "Gemini" };

/**
 * Two steps, as in xlrts: the form, then a confirmation of what will be
 * created. On confirm the gateway writes the config + subaccount (refusing to
 * overwrite either) and adds a window named after the market to the CUQuants
 * tmux session, with the venv active. It does not start the bot.
 */
export function LaunchMarketModal({ existing, root, onClose, onLaunched }: Props) {
  const [step, setStep] = useState<"form" | "confirm">("form");
  const [market, setMarket] = useState("");
  const [venues, setVenues] = useState<Record<Venue, ExchangeLaunchSettings>>(DEFAULTS);
  const [proxyExchange, setProxyExchange] = useState<"kraken" | "kraken_prime">("kraken_prime");
  const [error, setError] = useState("");
  const [launching, setLaunching] = useState(false);

  const name = market.trim().toUpperCase().replace(/\s+/g, "_");
  const project = root || "~/speedbyte";

  function setField(v: Venue, field: keyof ExchangeLaunchSettings, value: string | boolean) {
    setVenues((cur) => ({ ...cur, [v]: { ...cur[v], [field]: value } }));
  }

  function next() {
    if (!name) return setError("Market name is required.");
    if (!MARKET_RE.test(name) || name === "SAMPLE") return setError("Letters, digits, _ . - only.");
    if (existing.includes(name)) return setError(`${name} already exists.`);
    for (const v of Object.keys(venues) as Venue[]) {
      const s = venues[v];
      for (const f of ["minimum_spread", "center_buffer", "tick_level"] as const) {
        if (!/^-?\d+(\.\d+)?$/.test(s[f].trim())) return setError(`${LABELS[v]} ${f.replace("_", " ")} must be a number.`);
      }
      if (Number(s.tick_level) <= 0) return setError(`${LABELS[v]} tick level must be greater than 0.`);
    }
    setError("");
    setStep("confirm");
  }

  async function launch() {
    setLaunching(true);
    setError("");
    const trimmed = (s: ExchangeLaunchSettings): ExchangeLaunchSettings => ({
      ...s,
      trading_pair: s.trading_pair.trim(),
      reference_pair: s.reference_pair.trim(),
      minimum_spread: s.minimum_spread.trim(),
      center_buffer: s.center_buffer.trim(),
      tick_level: s.tick_level.trim(),
    });
    const req: LaunchMarketRequest = {
      market: name,
      okx: trimmed(venues.okx),
      kraken: { ...trimmed(venues.kraken), proxy_exchange: proxyExchange },
      gemini: trimmed(venues.gemini),
    };
    try {
      const res = await launchMarket(req);
      toast.success(
        res.where ? `${name} launched in ${res.where} — press Start when ready` : `${name} launched`,
      );
      if (!res.where) {
        toast("The gateway made a session, not a CUQuants window — it needs updating.", { icon: "⚠" });
      }
      onLaunched();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setLaunching(false);
    }
  }

  const input =
    "w-full rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 font-mono text-xs text-white/90 outline-none focus:border-sky-400/50";
  const label = "text-[11px] text-white/40";

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-40" onClick={launching ? undefined : onClose} />
      <div
        className="fixed left-1/2 top-1/2 z-50 w-[min(760px,calc(100vw-2rem))] max-h-[calc(100vh-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-white/10 bg-[#0d0d12] shadow-2xl"
        onKeyDown={(e) => {
          if (e.key === "Escape" && !launching) onClose();
          if (e.key === "Enter" && step === "form") next();
        }}
      >
        <div className="px-5 py-3 border-b border-white/10 bg-white/[0.03] text-sm font-semibold">
          {step === "form" ? "Launch Market" : "Confirm Launch"}
        </div>

        {step === "form" ? (
          <div className="p-5 space-y-5">
            <div className="max-w-xs">
              <div className={label}>Market name</div>
              <input
                autoFocus
                value={market}
                onChange={(e) => setMarket(e.target.value)}
                placeholder="USDT_USD"
                className={input}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(Object.keys(LABELS) as Venue[]).map((v) => {
                const s = venues[v];
                return (
                  <div key={v} className="rounded-md border border-white/[0.06] bg-white/[0.02] p-3 space-y-2">
                    <label className="flex items-center justify-between text-xs font-semibold text-sky-300 cursor-pointer">
                      {LABELS[v]}
                      <span className="flex items-center gap-1.5 text-white/50 font-normal">
                        <input
                          type="checkbox"
                          checked={s.enabled}
                          onChange={(e) => setField(v, "enabled", e.target.checked)}
                        />
                        enabled
                      </span>
                    </label>
                    {([
                      ["trading_pair", "Trading pair"],
                      ["reference_pair", "Ref pair"],
                      ["minimum_spread", "Min spread (bps)"],
                      ["center_buffer", "Center buffer (bps)"],
                      ["tick_level", "Tick level"],
                    ] as const).map(([f, l]) => (
                      <div key={f}>
                        <div className={label}>{l}</div>
                        <input
                          value={s[f]}
                          onChange={(e) => setField(v, f, e.target.value)}
                          className={input}
                        />
                      </div>
                    ))}
                    {v === "kraken" && (
                      <div>
                        <div className={label}>Proxy exchange</div>
                        <select
                          value={proxyExchange}
                          onChange={(e) => setProxyExchange(e.target.value as "kraken" | "kraken_prime")}
                          className={input}
                        >
                          <option value="kraken_prime">kraken_prime</option>
                          <option value="kraken">kraken</option>
                        </select>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="p-5 space-y-3 text-xs">
            <p className="text-white/80">The following will be created on the bot box:</p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 font-mono">
              <dt className="text-white/40">tmux window</dt>
              <dd>
                <span className="text-white/90">{name}</span>
                <span className="text-white/40"> — next window in the CUQuants session (cwd {project}, venv active)</span>
              </dd>
              <dt className="text-white/40">Config</dt>
              <dd className="text-white/90">{project}/data/configs/{name}.yaml</dd>
              <dt className="text-white/40">Subaccount</dt>
              <dd className="text-white/90">{project}/data/subaccounts/{name}.json</dd>
            </dl>
            <p className="text-white/40">The bot is not started. Check the files, then press Start.</p>
            <div className="rounded-md border border-white/[0.06] bg-white/[0.02] p-3 font-mono space-y-1">
              {(Object.keys(LABELS) as Venue[]).map((v) => (
                <div key={v} className="flex gap-3">
                  <span className="w-14 text-sky-300">{LABELS[v]}</span>
                  <span className={`w-16 ${venues[v].enabled ? "text-emerald-400" : "text-white/30"}`}>
                    {venues[v].enabled ? "enabled" : "disabled"}
                  </span>
                  <span className="text-white/60">pair={venues[v].trading_pair.trim() || "(none)"}</span>
                  <span className="text-white/60">ref={venues[v].reference_pair.trim() || "(none)"}</span>
                  {v === "kraken" && <span className="text-white/40">via {proxyExchange}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3 px-5 py-3 border-t border-white/10">
          {step === "form" ? (
            <button
              onClick={onClose}
              className="cursor-pointer rounded-md px-3 py-1.5 text-xs border border-white/10 text-white/50 hover:text-white/80"
            >
              Cancel
            </button>
          ) : (
            <button
              onClick={() => setStep("form")}
              disabled={launching}
              className="cursor-pointer rounded-md px-3 py-1.5 text-xs border border-white/10 text-white/50 hover:text-white/80 disabled:opacity-40"
            >
              ← Back
            </button>
          )}
          <span className="flex-1 text-xs text-red-400">{error}</span>
          {step === "form" ? (
            <button
              onClick={next}
              className="cursor-pointer rounded-md px-4 py-1.5 text-xs font-semibold border border-sky-400/30 text-sky-300 bg-sky-400/[0.08] hover:bg-sky-400/[0.15]"
            >
              Next →
            </button>
          ) : (
            <button
              onClick={() => void launch()}
              disabled={launching}
              className="cursor-pointer rounded-md px-4 py-1.5 text-xs font-semibold border border-emerald-400/30 text-emerald-300 bg-emerald-400/[0.08] hover:bg-emerald-400/[0.15] disabled:opacity-40"
            >
              {launching ? "Launching…" : "Launch ▶"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
