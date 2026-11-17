import type { OrderbookData, OrderbookLevel } from "../types/orderbook";

const formatPrice = (price: number) => price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 });
const formatQty = (qty: number) => qty >= 1000
  ? new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(qty)
  : qty.toLocaleString(undefined, { maximumFractionDigits: 6 });

export function StackedOrderbook({ data, pair }: { data: OrderbookData; pair: string }) {
  const bids = data.bids.slice(0, 8);
  const asks = data.asks.slice(0, 8);
  const max = Math.max(...bids.map(l => l.qty), ...asks.map(l => l.qty), 0);
  const bidQty = bids.reduce((sum, l) => sum + l.qty, 0);
  const askQty = asks.reduce((sum, l) => sum + l.qty, 0);
  const total = bidQty + askQty;
  const bidPercent = total > 0 ? bidQty / total * 100 : 50;
  const [base, quote = "USD"] = pair.split("/");

  function row(level: OrderbookLevel, side: "bid" | "ask") {
    return <div key={`${side}-${level.price}`} role="row" className="relative flex justify-between px-5 py-1.5 font-mono text-sm tabular-nums">
      <div aria-hidden="true" className={`absolute inset-y-0 right-0 ${side === "bid" ? "bg-emerald-500/15" : "bg-rose-500/15"}`} style={{ width: `${max > 0 ? level.qty / max * 100 : 0}%` }} />
      <span role="cell" className={`relative ${side === "bid" ? "text-emerald-400" : "text-rose-400"}`}>{formatPrice(level.price)}</span>
      <span role="cell" className="relative text-white/85">{formatQty(level.qty)}</span>
    </div>;
  }

  return <div role="table" aria-label={`Order book for ${pair}`} className="pb-3">
    <div role="row" className="flex justify-between px-5 py-3 text-xs text-white/40">
      <span role="columnheader">Price ({quote})</span><span role="columnheader">Quantity ({base})</span>
    </div>
    {asks.length ? [...asks].reverse().map(l => row(l, "ask")) : <p className="px-5 py-3 text-xs text-white/40">No asks available</p>}
    <div className="my-2 border-y border-white/10 px-5 py-3">
      <div className="mb-2 flex justify-between text-xs font-medium"><span className="text-emerald-400">Bids {total > 0 ? `${bidPercent.toFixed(1)}%` : "—"}</span><span className="text-rose-400">Asks {total > 0 ? `${(100 - bidPercent).toFixed(1)}%` : "—"}</span></div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-rose-500/70" aria-hidden="true"><div className="bg-emerald-500/80" style={{ width: `${bidPercent}%` }} /></div>
      <p className="mt-2 text-[10px] text-white/35">Quantity balance · nearest 8 levels per side</p>
    </div>
    {bids.length ? bids.map(l => row(l, "bid")) : <p className="px-5 py-3 text-xs text-white/40">No bids available</p>}
  </div>;
}
