import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { DepthChart } from "./components/DepthChart";
import { StackedOrderbook } from "./components/StackedOrderbook";
import type { OrderbookData } from "./types/orderbook";
import logo from "./assets/quants_dark.png";
import "./index.css";

// Fixed illustrative levels: this preview opens no exchange or order connections.
const data: OrderbookData = {
  symbol: "BTC/USD",
  bids: [
    { price: 77774.9, qty: 2.630232 }, { price: 77774.3, qty: .237570 },
    { price: 77774.2, qty: 1.920866 }, { price: 77773.6, qty: 2.485250 },
    { price: 77773.1, qty: .430061 }, { price: 77762.4, qty: 3.1 },
    { price: 77735.7, qty: 2.9 }, { price: 77700, qty: 3.6 },
  ],
  asks: [
    { price: 77775, qty: .638413 }, { price: 77775.9, qty: 1.025693 },
    { price: 77776.9, qty: .400061 }, { price: 77777.8, qty: 1.300110 },
    { price: 77779.3, qty: 2.100147 }, { price: 77790.2, qty: 2.8 },
    { price: 77812.6, qty: 3.2 }, { price: 77850, qty: 4.4 },
  ],
};

// This standalone preview entry mounts its only component here.
// eslint-disable-next-line react-refresh/only-export-components
function Concepts() {
  const [view, setView] = useState("book");
  return <div className="min-h-screen bg-black text-white">
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 px-6 py-4">
      <div className="flex items-center gap-3"><img src={logo} alt="CU Quants" className="h-9 w-auto"/><div><div className="text-lg font-bold">SharkLazer</div><div className="text-xs text-white/40">by CU Quants</div></div></div>
      <span className="rounded-full border border-blue-400/25 bg-blue-400/10 px-3 py-1 text-xs text-blue-300">Design concepts · sample data</span>
    </header>
    <main className="mx-auto max-w-6xl px-5 py-10">
      <p className="text-xs uppercase tracking-widest text-white/35">Kai Janipalli · CU Quants</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Order Book Layouts</h1>
      <p className="mt-3 max-w-xl text-sm leading-6 text-white/45">Used sample BTC data</p>
      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1fr_440px]">
        <section className="overflow-hidden rounded-xl border border-white/10 bg-[#0f0f0f]">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-4"><div><span className="text-[10px] uppercase tracking-widest text-white/35">Kraken</span><h2 className="mt-1 text-xl font-bold">BTC/USD</h2></div><div className="text-right"><span className="text-xs text-white/35">Spread</span><p className="mt-1 font-mono text-sm">$0.10</p></div></div>
          <div className="flex gap-1 border-b border-white/10 p-2" role="group" aria-label="Concept view">
            {[["book", "Order book"], ["depth", "Depth"]].map(([key, label]) => <button key={key} type="button" onClick={() => setView(key)} aria-pressed={view === key} className={`rounded-lg px-4 py-2 text-sm ${view === key ? "bg-white/10 text-white" : "text-white/40 hover:bg-white/5"}`}>{label}</button>)}
          </div>
          {view === "book" ? <StackedOrderbook data={data} pair="BTC/USD"/> : <DepthChart data={data}/>}
        </section>
        <aside className="space-y-5">
          <section className="overflow-hidden rounded-xl border border-white/10 bg-[#0f0f0f]"><div className="border-b border-white/10 px-5 py-4"><h2 className="text-sm font-semibold">Depth overview</h2></div><DepthChart data={data}/></section>
          <div className="rounded-xl border border-white/10 p-5 text-sm leading-6 text-white/45"><p className="font-medium text-white/80">Concept only</p><p className="mt-2">The stacked view puts asks above bids and uses bar length to show quantity. Depth accumulates those quantities outward from the midpoint.</p><p className="mt-3">Both fit the existing pair panel. Order entry and account connections are outside this preview.</p></div>
        </aside>
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><Concepts/></StrictMode>);
