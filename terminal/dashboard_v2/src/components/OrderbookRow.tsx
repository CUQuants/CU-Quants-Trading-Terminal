import type { OrderbookLevel } from "../types/orderbook";

interface OrderbookRowProps {
  level: OrderbookLevel;
  side: "bid" | "ask";
  maxQty: number;
}

export function OrderbookRow({ level, side, maxQty }: OrderbookRowProps) {
  const depthPercent = maxQty > 0 ? (level.qty / maxQty) * 100 : 0;
  const isBid = side === "bid";

  return (
    <div className="relative flex justify-between px-3 py-1 font-mono text-sm border-b border-white/5 hover:bg-white/5">
      <div
        className={`absolute top-0 bottom-0 opacity-15 transition-[width] duration-150 ease-out ${
          isBid
            ? "right-0 bg-gradient-to-l from-green-500 to-transparent"
            : "left-0 bg-gradient-to-r from-red-500 to-transparent"
        }`}
        style={{ width: `${depthPercent}%` }}
      />
      <span
        className={`z-10 font-medium ${isBid ? "text-green-500" : "text-red-500"}`}
      >
        {level.price.toLocaleString(undefined, {
          minimumFractionDigits: 1,
          maximumFractionDigits: 1,
        })}
      </span>
      <span className="z-10 text-white/70">{level.qty.toFixed(6)}</span>
    </div>
  );
}
