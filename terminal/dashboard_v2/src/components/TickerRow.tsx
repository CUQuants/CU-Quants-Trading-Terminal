import { useMemo } from "react";
import type { Exchange, OrderbookData } from "../types/orderbook";

interface Props {
  exchange: Exchange;
  pair: string;
  orderbook: OrderbookData | undefined;
  isSelected: boolean;
  onClick: () => void;
  onRemove: () => void;
}

export function TickerRow({
  exchange,
  pair,
  orderbook,
  isSelected,
  onClick,
  onRemove,
}: Props) {
  const spread = useMemo(() => {
    if (!orderbook || orderbook.bids.length === 0 || orderbook.asks.length === 0)
      return null;
    const bestBid = orderbook.bids[0].price;
    const bestAsk = orderbook.asks[0].price;
    const val = bestAsk - bestBid;
    return { value: val, percent: (val / bestAsk) * 100, bestBid, bestAsk };
  }, [orderbook]);

  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-4 px-5 py-3 cursor-pointer transition-colors border-b border-white/5 hover:bg-white/[0.04] ${
        isSelected ? "bg-white/[0.06] border-l-2 border-l-blue-500" : ""
      }`}
    >
      <span className="text-[10px] uppercase tracking-wider text-white/40 w-14">
        {exchange}
      </span>

      <span className="font-semibold text-white text-sm w-24">{pair}</span>

      {spread ? (
        <>
          <span className="font-mono text-sm text-green-500 w-28 text-right">
            {spread.bestBid.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
          <span className="font-mono text-sm text-red-500 w-28 text-right">
            {spread.bestAsk.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
          <span className="font-mono text-xs text-white/40 w-28 text-right">
            {spread.value.toFixed(2)} ({spread.percent.toFixed(3)}%)
          </span>
        </>
      ) : (
        <span className="text-xs text-white/30 italic">Waiting for data...</span>
      )}

      <div className="ml-auto">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="text-white/20 hover:text-red-400 transition-colors text-lg leading-none cursor-pointer"
          title="Remove pair"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
