import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { fetchAllOrders } from "../api/orders";
import { useCancelOrder } from "../hooks/useCancelOrder";
import type { Exchange } from "../types/orderbook";
import { BACKEND_EXCHANGES } from "../types/orderbook";
import type { Order } from "../types/orders";

const EXCHANGES = [...BACKEND_EXCHANGES];

interface Props {
  collapsed: boolean;
  onToggle: () => void;
}

function fmtPrice(n: number): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 5,
  });
}

function OpenOrderRow({ order }: { order: Order }) {
  const cancel = useCancelOrder(order.exchange);
  const isBuy = order.side === "buy";
  const notional = order.price != null ? order.price * order.size : null;

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 text-[11px] hover:bg-white/[0.03]"
      title={`Order ID: ${order.id}`}
    >
      <span className="w-10 shrink-0 uppercase tracking-wider text-white/40 text-[10px]">
        {order.exchange}
      </span>
      <span className="w-16 shrink-0 font-semibold text-white truncate">
        {order.pair}
      </span>
      <span
        className={`w-8 shrink-0 uppercase font-bold text-[10px] ${
          isBuy ? "text-green-500" : "text-red-500"
        }`}
      >
        {order.side}
      </span>
      <span
        className={`w-11 shrink-0 ${
          order.type === "iceberg" ? "text-cyan-400" : "text-white/60"
        }`}
      >
        {order.type}
      </span>
      <span className="flex-1 min-w-0 font-mono text-white text-right truncate">
        {order.price != null ? fmtPrice(order.price) : "Market"}
      </span>
      <span
        className="w-16 shrink-0 font-mono text-white/70 text-right truncate"
        title={
          order.visible_size != null
            ? `Visible: ${order.visible_size} / Total: ${order.size}`
            : undefined
        }
      >
        {order.size}
      </span>
      <span className="w-16 shrink-0 font-mono text-white/50 text-right truncate">
        {notional != null ? notional.toFixed(2) : ""}
      </span>
      <span className="w-12 shrink-0 uppercase text-white/40 text-[10px] truncate">
        {order.status}
      </span>
      <button
        onClick={() => cancel.mutate({ orderId: order.id, pair: order.pair })}
        disabled={cancel.isPending}
        className="shrink-0 text-white/30 hover:text-red-400 transition-colors text-base leading-none cursor-pointer disabled:opacity-30"
        title="Cancel order"
      >
        &times;
      </button>
    </div>
  );
}

/**
 * Collapsible sidebar listing every open order on the account, on every
 * exchange with a backend, like xlrts' `open_orders`. One REST call per
 * exchange (GET /orders/{exchange} with no pair), made only when the panel
 * is opened — never on a timer. Collapsing disables the queries; expanding
 * re-enables them, and because the data is stale (staleTime 0) that refetches.
 */
export function OpenOrdersPanel({ collapsed, onToggle }: Props) {
  const results = useQueries({
    queries: EXCHANGES.map((exchange: Exchange) => ({
      queryKey: ["openOrders", exchange],
      queryFn: () => fetchAllOrders(exchange),
      enabled: !collapsed,
      staleTime: 0,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    })),
  });

  const orders = useMemo(() => {
    const all = results.flatMap((r) => r.data ?? []);
    return all.sort(
      (a, b) =>
        a.exchange.localeCompare(b.exchange) ||
        a.pair.localeCompare(b.pair) ||
        // sells above buys, highest price first, like a ladder
        b.side.localeCompare(a.side) ||
        (b.price ?? 0) - (a.price ?? 0),
    );
  }, [results]);

  const isLoading = results.some((r) => r.isLoading);
  const failed = EXCHANGES.filter((_, i) => results[i].isError);

  if (collapsed) {
    return (
      <aside className="shrink-0 border-l border-white/10">
        <button
          onClick={onToggle}
          className="h-full w-8 flex flex-col items-center gap-2 py-3 text-white/40 hover:text-white hover:bg-white/[0.04] transition-colors cursor-pointer"
          title="Show open orders"
        >
          <span className="text-xs">&lsaquo;</span>
          <span className="text-[10px] uppercase tracking-wider [writing-mode:vertical-rl]">
            Open Orders{results.some((r) => r.data) ? ` (${orders.length})` : ""}
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="shrink-0 w-[480px] border-l border-white/10 flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <span className="text-[10px] uppercase tracking-wider text-white/50">
          Open Orders
          <span className="ml-2 text-white/30">{orders.length}</span>
        </span>
        <button
          onClick={onToggle}
          className="text-white/40 hover:text-white transition-colors text-xs cursor-pointer px-1"
          title="Collapse open orders"
        >
          &rsaquo;
        </button>
      </div>

      <div className="flex items-center gap-2 px-3 py-1.5 text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
        <span className="w-10 shrink-0">Exch</span>
        <span className="w-16 shrink-0">Pair</span>
        <span className="w-8 shrink-0">Side</span>
        <span className="w-11 shrink-0">Type</span>
        <span className="flex-1 min-w-0 text-right">Price</span>
        <span className="w-16 shrink-0 text-right">Size</span>
        <span className="w-16 shrink-0 text-right">Notional</span>
        <span className="w-12 shrink-0">Status</span>
        <span className="w-[9px] shrink-0" />
      </div>

      <div className="flex-1 overflow-y-auto">
        {orders.map((order) => (
          <OpenOrderRow key={`${order.exchange}-${order.id}`} order={order} />
        ))}
        {orders.length === 0 && (
          <div className="py-6 text-center text-white/30 text-xs">
            {isLoading ? "Loading orders..." : "No open orders"}
          </div>
        )}
        {failed.length > 0 && (
          <div className="py-2 text-center text-red-400 text-xs">
            Failed to load orders for {failed.join(", ")}
          </div>
        )}
      </div>

      <div className="px-3 py-1.5 border-t border-white/10 text-[10px] text-white/30">
        Total: {orders.length} order{orders.length === 1 ? "" : "s"} · all pairs
      </div>
    </aside>
  );
}
