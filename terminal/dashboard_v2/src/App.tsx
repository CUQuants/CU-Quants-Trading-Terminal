import { useState } from "react";
import type { Exchange } from "./types/orderbook";
import { EXCHANGE_SYMBOLS } from "./types/orderbook";
import { KrakenView, OkxView } from "./components";

function App() {
  const [exchange, setExchange] = useState<Exchange>("kraken");
  const [symbol, setSymbol] = useState(EXCHANGE_SYMBOLS.kraken[0]);

  const handleExchangeChange = (newExchange: Exchange) => {
    setExchange(newExchange);
    setSymbol(EXCHANGE_SYMBOLS[newExchange][0]);
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="flex justify-between items-center px-6 py-5 border-b border-white/10 bg-white/[0.02]">
        <h1 className="text-2xl font-bold bg-gradient-to-br from-white to-gray-500 bg-clip-text text-transparent">
          Orderbook Viewer
        </h1>

        <div className="flex items-center gap-4">
          {/* Exchange selector */}
          <select
            value={exchange}
            onChange={(e) => handleExchangeChange(e.target.value as Exchange)}
            className="px-3 py-2 text-sm rounded-lg border border-white/20 bg-white/5 text-white cursor-pointer outline-none transition-all hover:border-white/30 focus:border-blue-500"
          >
            <option value="kraken">Kraken</option>
            <option value="okx">OKX</option>
          </select>

          {/* Symbol selector */}
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-white/20 bg-white/5 text-white cursor-pointer outline-none transition-all hover:border-white/30 focus:border-blue-500"
          >
            {EXCHANGE_SYMBOLS[exchange].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Main content */}
      <main className="p-6">
        {exchange === "kraken" ? (
          <KrakenView key={`kraken-${symbol}`} symbol={symbol} />
        ) : (
          <OkxView key={`okx-${symbol}`} symbol={symbol} />
        )}
      </main>
    </div>
  );
}

export default App;
