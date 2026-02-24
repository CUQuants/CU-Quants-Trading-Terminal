import { useOkxWs } from "../contexts/OkxWsContext";
import { useKrakenWs } from "../contexts/KrakenWsContext";
import { useOrderEvents } from "../contexts/OrderEventsContext";

const STATUS_COLORS: Record<string, string> = {
  connected: "bg-green-500 shadow-[0_0_6px_theme(colors.green.500)]",
  connecting: "bg-yellow-500 animate-pulse",
  reconnecting: "bg-yellow-500 animate-pulse",
  disconnected: "bg-red-500",
  failed: "bg-red-500",
  idle: "bg-white/20",
};

function StatusDot({ status, label }: { status: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-white/60">
      <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[status] ?? "bg-white/20"}`} />
      <span>{label}</span>
    </div>
  );
}

export function DashboardHeader() {
  const okxWs = useOkxWs();
  const krakenWs = useKrakenWs();
  const { orderEventsStatus } = useOrderEvents();

  return (
    <header className="flex justify-between items-center px-6 py-4 border-b border-white/10 bg-gradient-to-r from-white/[0.03] to-transparent">
      <div className="flex items-center gap-3">
        <span className="text-2xl leading-none">📊</span>
        <div>
          <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent leading-tight">
            CU Quants Trading Terminal
          </h1>
          <span className="text-[10px] uppercase tracking-widest text-white/25">
            Live Market Data
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 bg-white/[0.03] rounded-lg px-3 py-1.5 border border-white/5">
          <span className="text-[10px] uppercase tracking-widest text-white/30 mr-1">
            Book
          </span>
          <StatusDot status={krakenWs.connectionStatus} label="Kraken" />
          <StatusDot status={okxWs.connectionStatus} label="OKX" />
        </div>

        <div className="flex items-center gap-3 bg-white/[0.03] rounded-lg px-3 py-1.5 border border-white/5">
          <span className="text-[10px] uppercase tracking-widest text-white/30 mr-1">
            Orders
          </span>
          <StatusDot status={orderEventsStatus.kraken} label="Kraken" />
          <StatusDot status={orderEventsStatus.okx} label="OKX" />
        </div>
      </div>
    </header>
  );
}
