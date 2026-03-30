import type { Order } from "../types/orders";

interface Props {
  order: Order;
  onCancel: (orderId: string) => void;
  isCancelling: boolean;
}

export function OrderItem({ order, onCancel, isCancelling }: Props) {
  const isBuy = order.side === "buy";

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/5 text-sm">
      <span
        className={`text-[10px] uppercase font-bold w-10 ${
          isBuy ? "text-green-500" : "text-red-500"
        }`}
      >
        {order.side}
      </span>

      <span className="text-white/60 w-14">
        {order.type === "iceberg" ? (
          <span className="text-cyan-400" title="Iceberg order">iceberg</span>
        ) : (
          order.type
        )}
      </span>

      <span className="font-mono text-white w-24 text-right">
        {order.price != null
          ? order.price.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 5,
            })
          : "Market"}
      </span>

      <span className="font-mono text-white/70 w-20 text-right" title={
        order.visible_size != null
          ? `Visible: ${order.visible_size} / Total: ${order.size}`
          : undefined
      }>
        {order.visible_size != null ? `${order.visible_size}/${order.size}` : order.size}
      </span>

      <span className="text-[10px] uppercase text-white/40 w-20">
        {order.status}
      </span>

      <button
        onClick={() => onCancel(order.id)}
        disabled={isCancelling}
        className="ml-auto text-xs px-2.5 py-1 rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer disabled:opacity-30"
      >
        Cancel
      </button>
    </div>
  );
}
