import { useMemo } from "react";
import type { OrderbookLevel } from "../types/orderbook";
import { OrderbookRow } from "./OrderbookRow";

interface OrderbookSideProps {
  levels: OrderbookLevel[];
  side: "bid" | "ask";
  title: string;
}

export function OrderbookSide({ levels, side, title }: OrderbookSideProps) {
  const maxQty = useMemo(
    () => Math.max(...levels.map((l) => l.qty), 0),
    [levels]
  );

  const totalQty = useMemo(
    () => levels.reduce((sum, l) => sum + l.qty, 0),
    [levels]
  );

  const displayLevels = side === "ask" ? [...levels].reverse() : levels;

  return (
    <div className="flex flex-1 flex-col min-w-[280px]">
      <div className="flex justify-between items-center px-3 py-3 border-b border-white/10">
        <span
          className={`font-semibold text-sm ${
            side === "bid" ? "text-green-500" : "text-red-500"
          }`}
        >
          {title}
        </span>
        <span className="text-xs text-white/50">
          Total: {totalQty.toFixed(4)}
        </span>
      </div>
      <div className="flex justify-between px-3 py-2 text-[11px] uppercase tracking-wide text-white/40 border-b border-white/10">
        <span>Price (USD)</span>
        <span>Quantity</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {displayLevels.map((level) => (
          <OrderbookRow
            key={level.price}
            level={level}
            side={side}
            maxQty={maxQty}
          />
        ))}
      </div>
    </div>
  );
}
