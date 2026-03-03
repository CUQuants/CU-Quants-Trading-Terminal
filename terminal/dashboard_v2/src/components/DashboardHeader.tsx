import { useOkxWs } from "../contexts/OkxWsContext";
import { useKrakenWs } from "../contexts/KrakenWsContext";
import { useOrderEvents } from "../contexts/OrderEventsContext";

export type View = "dashboard" | "trades" | "account";

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

function TabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`cursor-pointer px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
        active
          ? "bg-white/10 text-white"
          : "text-white/40 hover:text-white/60 hover:bg-white/[0.04]"
      }`}
    >
      {label}
    </button>
  );
}

interface HeaderProps {
  currentView: View;
  onViewChange: (view: View) => void;
}

export function DashboardHeader({ currentView, onViewChange }: HeaderProps) {
  const okxWs = useOkxWs();
  const krakenWs = useKrakenWs();
  const { orderEventsStatus } = useOrderEvents();

  return (
    <header className="flex justify-between items-center px-6 py-4 border-b border-white/10 bg-gradient-to-r from-white/[0.03] to-transparent">
      <div className="flex items-center gap-6">
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

        <div className="flex items-center gap-1 bg-white/[0.03] rounded-lg p-1 border border-white/5">
          <TabButton
            label="Dashboard"
            active={currentView === "dashboard"}
            onClick={() => onViewChange("dashboard")}
          />
          <TabButton
            label="Trades"
            active={currentView === "trades"}
            onClick={() => onViewChange("trades")}
          />
          <TabButton
            label="Account"
            active={currentView === "account"}
            onClick={() => onViewChange("account")}
          />
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
