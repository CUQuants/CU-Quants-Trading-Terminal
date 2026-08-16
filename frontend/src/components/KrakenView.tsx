import { useKrakenOrderbook } from "../hooks";
import { Orderbook } from "./Orderbook";

interface KrakenViewProps {
  symbol: string;
  depth?: number;
}

export function KrakenView({ symbol, depth = 10 }: KrakenViewProps) {
  const { orderbook, isConnected, error, connect, disconnect } =
    useKrakenOrderbook({ symbol, depth });

  return (
    <div className="flex flex-col gap-4">
      {/* Connection bar */}
      <div className="flex items-center justify-end gap-4">
        <div className="flex items-center gap-2 text-sm text-white/70">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected
                ? "bg-green-500 shadow-[0_0_8px_theme(colors.green.500)]"
                : "bg-red-500"
            }`}
          />
          <span>{isConnected ? "Live" : "Disconnected"}</span>
        </div>
        <button
          onClick={isConnected ? disconnect : connect}
          className={`px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition-all ${
            isConnected
              ? "bg-red-500/20 text-red-500 border border-red-500 hover:bg-red-500/30"
              : "bg-green-500 text-black border-none hover:bg-green-600"
          }`}
        >
          {isConnected ? "Disconnect" : "Connect"}
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded-lg text-center">
          {error}
        </div>
      )}

      {orderbook ? (
        <Orderbook data={orderbook} exchange="kraken" pair={symbol} />
      ) : (
        <div className="text-center py-16 text-white/50 text-base">
          {isConnected ? "Waiting for data..." : "Click Connect to start"}
        </div>
      )}
    </div>
  );
}
