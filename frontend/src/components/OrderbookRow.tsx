import type { OrderbookLevel } from "../types/orderbook";

interface OrderbookRowProps {
  level: OrderbookLevel;
  side: "bid" | "ask";
  maxQty: number;
  hasMyOrder?: boolean;
  onPriceSelect?: (price: number) => void;
}

export function OrderbookRow({ level, side, maxQty, hasMyOrder, onPriceSelect }: OrderbookRowProps) {
  const depthPercent = maxQty > 0 ? (level.qty / maxQty) * 100 : 0;
  const isBid = side === "bid";

  return (
    <div
      className={`relative flex justify-between px-3 py-1 font-mono text-sm border-b border-white/5 hover:bg-white/5 ${
        hasMyOrder ? "ring-1 ring-inset ring-yellow-400/60 bg-yellow-400/[0.06]" : ""
      }`}
    >
      <div
        className={`absolute top-0 bottom-0 opacity-15 transition-[width] duration-150 ease-out ${
          isBid
            ? "right-0 bg-gradient-to-l from-green-500 to-transparent"
            : "left-0 bg-gradient-to-r from-red-500 to-transparent"
        }`}
        style={{ width: `${depthPercent}%` }}
      />
      <button
        type="button"
        disabled={!onPriceSelect}
        onClick={() => onPriceSelect?.(level.price)}
        aria-label={`Use ${side} price ${level.price}`}
        className={`z-10 font-medium rounded focus-visible:outline-2 focus-visible:outline-blue-400 enabled:cursor-pointer enabled:hover:underline ${isBid ? "text-green-500" : "text-red-500"}`}
      >
        {level.price.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 5,
        })}
      </button>
      {hasMyOrder && (
        <span className="z-10 text-yellow-400 text-[10px] self-center mx-1">●</span>
      )}
      <span className="z-10 text-white/70">{level.qty.toFixed(6)}</span>
    </div>
  );
}
