import { useMemo } from "react";
import type { Exchange, OrderbookData } from "../types/orderbook";
import { useActiveOrders } from "../contexts/ActiveOrdersContext";
import { OrderbookSide } from "./OrderbookSide";

const VISIBLE_LEVELS = 5;

interface OrderbookProps {
  data: OrderbookData;
  exchange: Exchange;
  pair: string;
}

export function Orderbook({ data, exchange, pair }: OrderbookProps) {
  const { hasOrderAtPrice } = useActiveOrders();

  const spread = useMemo(() => {
    if (data.bids.length === 0 || data.asks.length === 0) return null;
    const bestBid = data.bids[0].price;
    const bestAsk = data.asks[0].price;
    const spreadValue = bestAsk - bestBid;
    const mid = (bestBid + bestAsk) / 2;
    const bps = mid > 0 ? (spreadValue / mid) * 10000 : 0;
    return { value: spreadValue, bps, bestBid, bestAsk };
  }, [data.bids, data.asks]);

  const visibleBids = data.bids.slice(0, VISIBLE_LEVELS);
  const visibleAsks = data.asks.slice(0, VISIBLE_LEVELS);

  const activePrices = useMemo(() => {
    const set = new Set<number>();
    for (const level of [...visibleBids, ...visibleAsks]) {
      if (hasOrderAtPrice(exchange, pair, level.price)) {
        set.add(level.price);
      }
    }
    return set;
  }, [visibleBids, visibleAsks, hasOrderAtPrice, exchange, pair]);

  return (
    <div className="bg-[#0f0f0f] rounded-xl border border-white/10 overflow-hidden max-w-[800px] mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center px-5 py-4 bg-white/[0.02] border-b border-white/10">
        <h2 className="text-xl font-bold text-white m-0">{data.symbol}</h2>
        {spread && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/50">Spread:</span>
            <span className="text-sm text-white/80 font-mono">
              ${spread.value.toFixed(2)} ({spread.bps.toFixed(1)} bps)
            </span>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex flex-col sm:flex-row">
        <OrderbookSide
          levels={visibleBids}
          side="bid"
          title="Bids"
          activePrices={activePrices}
        />

        {/* Spread divider */}
        <div className="flex justify-center items-center p-3 bg-white/[0.03] border-t border-b border-white/10 sm:border-t-0 sm:border-b-0 sm:border-l sm:border-r sm:flex-col sm:px-4 sm:py-5">
          {spread && (
            <div className="flex items-center gap-3 font-mono text-sm sm:flex-col sm:gap-1">
              <span className="text-green-500 font-semibold">
                {spread.bestBid.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-white/30 sm:rotate-90">↔</span>
              <span className="text-red-500 font-semibold">
                {spread.bestAsk.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          )}
        </div>

        <OrderbookSide
          levels={visibleAsks}
          side="ask"
          title="Asks"
          activePrices={activePrices}
        />
      </div>
    </div>
  );
}
