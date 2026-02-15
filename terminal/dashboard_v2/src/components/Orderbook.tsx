import { useMemo } from "react";
import type { OrderbookData } from "../types/orderbook";
import { OrderbookSide } from "./OrderbookSide";

interface OrderbookProps {
  data: OrderbookData;
}

export function Orderbook({ data }: OrderbookProps) {
  const spread = useMemo(() => {
    if (data.bids.length === 0 || data.asks.length === 0) return null;
    const bestBid = data.bids[0].price;
    const bestAsk = data.asks[0].price;
    const spreadValue = bestAsk - bestBid;
    const spreadPercent = (spreadValue / bestAsk) * 100;
    return { value: spreadValue, percent: spreadPercent, bestBid, bestAsk };
  }, [data.bids, data.asks]);

  return (
    <div className="bg-[#0f0f0f] rounded-xl border border-white/10 overflow-hidden max-w-[800px] mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center px-5 py-4 bg-white/[0.02] border-b border-white/10">
        <h2 className="text-xl font-bold text-white m-0">{data.symbol}</h2>
        {spread && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/50">Spread:</span>
            <span className="text-sm text-white/80 font-mono">
              ${spread.value.toFixed(2)} ({spread.percent.toFixed(3)}%)
            </span>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex flex-col sm:flex-row">
        <OrderbookSide levels={data.bids} side="bid" title="Bids" />

        {/* Spread divider */}
        <div className="flex justify-center items-center p-3 bg-white/[0.03] border-t border-b border-white/10 sm:border-t-0 sm:border-b-0 sm:border-l sm:border-r sm:flex-col sm:px-4 sm:py-5">
          {spread && (
            <div className="flex items-center gap-3 font-mono text-sm sm:flex-col sm:gap-1">
              <span className="text-green-500 font-semibold">
                {spread.bestBid.toLocaleString()}
              </span>
              <span className="text-white/30 sm:rotate-90">↔</span>
              <span className="text-red-500 font-semibold">
                {spread.bestAsk.toLocaleString()}
              </span>
            </div>
          )}
        </div>

        <OrderbookSide levels={data.asks} side="ask" title="Asks" />
      </div>
    </div>
  );
}
