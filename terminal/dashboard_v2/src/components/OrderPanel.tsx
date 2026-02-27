import type { Exchange, OrderbookData } from "../types/orderbook";
import { Orderbook } from "./Orderbook";
import { OrderList } from "./OrderList";
import { OrderPlacementForm } from "./OrderPlacementForm";

interface Props {
  exchange: Exchange;
  pair: string;
  orderbook: OrderbookData | undefined;
  onClose: () => void;
}

export function OrderPanel({ exchange, pair, orderbook, onClose }: Props) {
  return (
    <div className="fixed inset-y-0 right-0 w-[480px] bg-[#0a0a0a] border-l border-white/10 flex flex-col z-50 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 bg-white/[0.02]">
        <div>
          <span className="text-[10px] uppercase tracking-wider text-white/40">
            {exchange}
          </span>
          <h2 className="text-lg font-bold text-white">{pair}</h2>
        </div>
        <button
          onClick={onClose}
          className="text-white/30 hover:text-white text-2xl leading-none transition-colors cursor-pointer"
        >
          &times;
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Orderbook */}
        <div className="border-b border-white/10">
          {orderbook ? (
            <Orderbook data={orderbook} exchange={exchange} pair={pair} />
          ) : (
            <div className="py-8 text-center text-white/30 text-sm">
              Waiting for orderbook data...
            </div>
          )}
        </div>

        {/* Open orders */}
        <div className="border-b border-white/10">
          <div className="px-4 py-3 border-b border-white/10">
            <h3 className="text-xs uppercase tracking-wider text-white/50 font-semibold">
              Open Orders
            </h3>
          </div>
          <OrderList exchange={exchange} pair={pair} />
        </div>

        {/* Place order */}
        <div>
          <div className="px-4 py-3 border-b border-white/10">
            <h3 className="text-xs uppercase tracking-wider text-white/50 font-semibold">
              Place Order
            </h3>
          </div>
          <OrderPlacementForm exchange={exchange} pair={pair} />
        </div>
      </div>
    </div>
  );
}
