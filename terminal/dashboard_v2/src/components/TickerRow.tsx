import { useMemo } from "react";
import type { Exchange, OrderbookData, OrderbookLevel } from "../types/orderbook";

const VISIBLE = 5;

interface Props {
  exchange: Exchange;
  pair: string;
  orderbook: OrderbookData | undefined;
  isSelected: boolean;
  onClick: () => void;
  onRemove: () => void;
}

function fmt(n: number) {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function MiniLevel({
  level,
  side,
  depthPct,
}: {
  level: OrderbookLevel;
  side: "bid" | "ask";
  depthPct: number;
}) {
  const isBid = side === "bid";
  return (
    <div className="relative flex-1 min-w-0 px-1 py-0.5">
      <div
        className={`absolute inset-0 opacity-20 ${
          isBid ? "bg-green-500" : "bg-red-500"
        }`}
        style={{
          width: `${depthPct}%`,
          [isBid ? "right" : "left"]: 0,
          [isBid ? "left" : "right"]: "auto",
          position: "absolute",
        }}
      />
      <span
        className={`relative font-mono text-[11px] block truncate ${
          isBid ? "text-green-400 text-right" : "text-red-400 text-left"
        }`}
      >
        {fmt(level.price)}
      </span>
    </div>
  );
}

export function TickerRow({
  exchange,
  pair,
  orderbook,
  isSelected,
  onClick,
  onRemove,
}: Props) {
  const { bidLevels, askLevels, maxQty, spread } = useMemo(() => {
    if (!orderbook || orderbook.bids.length === 0 || orderbook.asks.length === 0)
      return { bidLevels: [], askLevels: [], maxQty: 0, spread: null };

    const bids = orderbook.bids.slice(0, VISIBLE);
    const asks = orderbook.asks.slice(0, VISIBLE);
    const allQty = [...bids, ...asks].map((l) => l.qty);
    const bestBid = bids[0].price;
    const bestAsk = asks[0].price;
    const val = bestAsk - bestBid;

    return {
      bidLevels: [...bids].reverse(),
      askLevels: asks,
      maxQty: Math.max(...allQty, 0),
      spread: { value: val, percent: (val / bestAsk) * 100 },
    };
  }, [orderbook]);

  const hasData = bidLevels.length > 0 && askLevels.length > 0;

  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-2 cursor-pointer transition-colors border-b border-white/5 hover:bg-white/[0.04] ${
        isSelected ? "bg-white/[0.06] border-l-2 border-l-blue-500" : ""
      }`}
    >
      <span className="text-[10px] uppercase tracking-wider text-white/40 w-12 shrink-0">
        {exchange}
      </span>
      <span className="font-semibold text-white text-sm w-20 shrink-0">{pair}</span>

      {hasData ? (
        <>
          <div className="flex flex-1 min-w-0 items-center">
            {/* Bids: low → high (left → right) */}
            <div className="flex flex-1 min-w-0">
              {bidLevels.map((l) => (
                <MiniLevel
                  key={l.price}
                  level={l}
                  side="bid"
                  depthPct={maxQty > 0 ? (l.qty / maxQty) * 100 : 0}
                />
              ))}
            </div>

            {/* Spread pill */}
            <div className="shrink-0 px-2 mx-1 py-0.5 rounded bg-white/5 border border-white/10">
              <span className="font-mono text-[10px] text-white/40 whitespace-nowrap">
                {spread!.value.toFixed(2)}
              </span>
            </div>

            {/* Asks: low → high (left → right) */}
            <div className="flex flex-1 min-w-0">
              {askLevels.map((l) => (
                <MiniLevel
                  key={l.price}
                  level={l}
                  side="ask"
                  depthPct={maxQty > 0 ? (l.qty / maxQty) * 100 : 0}
                />
              ))}
            </div>
          </div>
        </>
      ) : (
        <span className="text-xs text-white/30 italic flex-1">
          Waiting for data...
        </span>
      )}

      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="text-white/20 hover:text-red-400 transition-colors text-lg leading-none cursor-pointer shrink-0 ml-2"
        title="Remove pair"
      >
        &times;
      </button>
    </div>
  );
}
