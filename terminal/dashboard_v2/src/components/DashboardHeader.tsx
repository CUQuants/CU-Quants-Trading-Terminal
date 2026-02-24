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
    <header className="flex justify-between items-center px-6 py-4 border-b border-white/10 bg-white/[0.02]">
      <h1 className="text-xl font-bold bg-gradient-to-br from-white to-gray-500 bg-clip-text text-transparent">
        Terminal Bear
      </h1>

      <div className="flex items-center gap-5">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-widest text-white/30">
            Orderbook
          </span>
          <StatusDot status={krakenWs.connectionStatus} label="Kraken" />
          <StatusDot status={okxWs.connectionStatus} label="OKX" />
        </div>

        <div className="w-px h-4 bg-white/10" />

        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-widest text-white/30">
            Orders
          </span>
          <StatusDot status={orderEventsStatus.kraken} label="Kraken" />
          <StatusDot status={orderEventsStatus.okx} label="OKX" />
        </div>
      </div>
    </header>
  );
}
