import type { Exchange } from "../types/orderbook";
import { useOrders } from "../hooks/useOrders";
import { useCancelOrder } from "../hooks/useCancelOrder";
import { OrderItem } from "./OrderItem";

interface Props {
  exchange: Exchange;
  pair: string;
}

export function OrderList({ exchange, pair }: Props) {
  const { data: orders, isLoading, isError } = useOrders(exchange, pair);
  const cancelMutation = useCancelOrder(exchange);

  if (isLoading) {
    return (
      <div className="py-6 text-center text-white/30 text-sm">
        Loading orders...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-6 text-center text-red-400 text-sm">
        Failed to load orders
      </div>
    );
  }

  if (!orders || orders.length === 0) {
    return (
      <div className="py-6 text-center text-white/30 text-sm">
        No open orders
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 px-4 py-2 text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
        <span className="w-10">Side</span>
        <span className="w-14">Type</span>
        <span className="w-24 text-right">Price</span>
        <span className="w-20 text-right">Size</span>
        <span className="w-20">Status</span>
        <span className="ml-auto" />
      </div>
      {orders.map((order) => (
        <OrderItem
          key={order.id}
          order={order}
          onCancel={(orderId) =>
            cancelMutation.mutate({ orderId, pair })
          }
          isCancelling={cancelMutation.isPending}
        />
      ))}
    </div>
  );
}
