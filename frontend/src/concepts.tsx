import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { KrakenWsProvider, useKrakenWs } from "./contexts/KrakenWsContext";
import { OkxWsProvider, useOkxWs } from "./contexts/OkxWsContext";
import { GeminiWsProvider, useGeminiWs } from "./contexts/GeminiWsContext";
import { EXCHANGE_SYMBOLS, type Exchange } from "./types/orderbook";
import { StackedOrderbook } from "./components/StackedOrderbook";
import { DepthChart } from "./components/DepthChart";
import "./index.css";

// eslint-disable-next-line react-refresh/only-export-components
function LiveConcepts() {
  const [exchange, setExchange] = useState<Exchange>("kraken");
  const [pair, setPair] = useState("BTC/USD");
  const kraken = useKrakenWs();
  const okx = useOkxWs();
  const gemini = useGeminiWs();
  const feed = { kraken, okx, gemini }[exchange];
  const { subscribe, unsubscribe } = feed;
  useEffect(() => {
    subscribe(pair);
    return () => unsubscribe(pair);
  }, [subscribe, unsubscribe, pair]);
  const data = feed.orderbook[pair];
  const error = feed.pairErrors[pair];
  const ready = feed.connectionStatus === "connected" && data && !error;
  const displayPair = exchange === "okx" ? pair.replace("/USD", "/USDT") : pair;
  return <main className="min-h-screen bg-black px-5 py-8 text-white">
    <div className="mx-auto max-w-5xl">
      <p className="text-xs text-white/40">Kai Janipalli · CU Quants</p>
      <h1 className="mt-2 text-2xl font-semibold">Order Book Layouts</h1>
      <div className="my-6 flex flex-wrap items-center gap-4">
        <label>Exchange <select aria-label="Exchange" value={exchange} onChange={e => setExchange(e.target.value as Exchange)} className="rounded border border-white/20 bg-neutral-900 p-2">{(["kraken", "okx", "gemini"] as const).map(e => <option key={e}>{e}</option>)}</select></label>
        <label>Pair <select aria-label="Pair" value={pair} onChange={e => setPair(e.target.value)} className="rounded border border-white/20 bg-neutral-900 p-2">{EXCHANGE_SYMBOLS[exchange].map(p => <option key={p} value={p}>{exchange === "okx" ? p.replace("/USD", "/USDT") : p}</option>)}</select></label>
        <p role="status" className="text-sm text-white/50">{exchange} · {feed.connectionStatus}</p>
        <a href="/" className="text-sm text-blue-400 underline">Trading dashboard</a>
      </div>
      <p className="mb-4 text-sm text-white/45">{displayPair} · Exchange WebSocket data</p>
      {error && <p role="alert" className="mb-4 text-red-400">{error}</p>}
      {ready ? <div className="grid items-start gap-6 md:grid-cols-2">
        <section className="rounded-xl border border-white/10 bg-[#0f0f0f]"><h2 className="border-b border-white/10 px-5 py-4 font-semibold">Order book</h2><StackedOrderbook data={data} pair={displayPair}/></section>
        <section className="rounded-xl border border-white/10 bg-[#0f0f0f]"><h2 className="border-b border-white/10 px-5 py-4 font-semibold">Depth</h2><DepthChart data={data}/></section>
      </div> : <p className="py-16 text-center text-white/40">Waiting for a connected feed and an order-book snapshot.</p>}
    </div>
  </main>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode><KrakenWsProvider><OkxWsProvider><GeminiWsProvider><LiveConcepts/></GeminiWsProvider></OkxWsProvider></KrakenWsProvider></StrictMode>,
);
