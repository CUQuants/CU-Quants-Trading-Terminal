import { useId, useState } from "react";
import type { OrderbookData, OrderbookLevel } from "../types/orderbook";

const ranges = [0.1, 0.5, 1, 2, 5];
const priceLabel = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 5 });

/** Cumulative quantity plotted against price; each level adds a vertical step. */
export function DepthChart({ data }: { data: OrderbookData }) {
  const [rangeIndex, setRangeIndex] = useState(1);
  const id = useId().replace(/:/g, "");
  const bestBid = data.bids[0]?.price;
  const bestAsk = data.asks[0]?.price;
  if (bestBid === undefined || bestAsk === undefined) {
    return <p className="px-5 py-16 text-center text-sm text-white/40">Waiting for both bids and asks to display depth.</p>;
  }
  const mid = (bestBid + bestAsk) / 2;
  const halfRange = mid * ranges[rangeIndex] / 100;
  if (halfRange <= 0) return <p className="p-5 text-white/40">Depth unavailable for this price.</p>;
  const low = mid - halfRange;
  const high = mid + halfRange;
  const bids = data.bids.filter(l => l.price >= low && l.price <= mid);
  const asks = data.asks.filter(l => l.price <= high && l.price >= mid);
  const sum = (levels: OrderbookLevel[]) => levels.reduce((total, l) => total + l.qty, 0);
  const bidTotal = sum(bids);
  const askTotal = sum(asks);
  const maxQty = Math.max(bidTotal, askTotal, 1e-12);
  const x = (price: number) => 20 + (price - low) / (high - low) * 560;
  const y = (qty: number) => 240 - qty / maxQty * 200;
  function path(levels: OrderbookLevel[], edge: number) {
    let qty = 0;
    let d = `M ${x(mid)} 240`;
    for (const level of levels) {
      d += ` H ${x(level.price)}`;
      qty += level.qty;
      d += ` V ${y(qty)}`;
    }
    return `${d} H ${x(edge)}`;
  }
  const bidPath = path(bids, low);
  const askPath = path(asks, high);
  return <div className="p-4">
    <div className="mb-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button type="button" aria-label="Decrease price range" disabled={rangeIndex === 0} onClick={() => setRangeIndex(i => i - 1)} className="rounded px-3 py-1 text-white/70 hover:bg-white/10 disabled:opacity-25">−</button>
        <span className="min-w-16 text-center font-mono text-sm text-white/80">±{ranges[rangeIndex]}%</span>
        <button type="button" aria-label="Increase price range" disabled={rangeIndex === ranges.length - 1} onClick={() => setRangeIndex(i => i + 1)} className="rounded px-3 py-1 text-white/70 hover:bg-white/10 disabled:opacity-25">+</button>
      </div>
      <span className="text-[10px] text-white/35">Cumulative quantity</span>
    </div>
    <div className="flex justify-between text-xs"><span className="text-emerald-400">Bids {priceLabel(bidTotal)}</span><span className="text-rose-400">Asks {priceLabel(askTotal)}</span></div>
    <svg viewBox="0 0 600 270" role="img" aria-label={`Cumulative market depth for ${data.symbol}, within ${ranges[rangeIndex]} percent of midpoint ${priceLabel(mid)}`} className="mt-2 w-full">
      <defs>{[["bid", "#34d399"], ["ask", "#fb7185"]].map(([side, color]) => <linearGradient key={side} id={`${id}-${side}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity=".3"/><stop offset="100%" stopColor={color} stopOpacity=".02"/></linearGradient>)}</defs>
      {[40, 140, 240].map(line => <line key={line} x1="20" x2="580" y1={line} y2={line} stroke="white" strokeOpacity=".07"/>)}
      <line x1="300" x2="300" y1="20" y2="240" stroke="white" strokeOpacity=".25" strokeDasharray="4 5"/>
      <path d={`${bidPath} V 240 Z`} fill={`url(#${id}-bid)`}/><path d={bidPath} fill="none" stroke="#34d399" strokeWidth="2"/>
      <path d={`${askPath} V 240 Z`} fill={`url(#${id}-ask)`}/><path d={askPath} fill="none" stroke="#fb7185" strokeWidth="2"/>
      <text x="20" y="263" fill="#34d399" fontSize="12">{priceLabel(low)}</text>
      <text x="300" y="263" textAnchor="middle" fill="#aaa" fontSize="12">{priceLabel(mid)}</text>
      <text x="580" y="263" textAnchor="end" fill="#fb7185" fontSize="12">{priceLabel(high)}</text>
    </svg>
    <p className="mt-2 text-[10px] leading-relaxed text-white/35">Price on horizontal axis · quantity on vertical axis (0–{priceLabel(maxQty)}). Uses available subscribed levels; flat edges may indicate the feed’s depth limit.</p>
  </div>;
}
