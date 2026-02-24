import { useState } from "react";
import type { Exchange } from "../types/orderbook";
import { EXCHANGE_SYMBOLS } from "../types/orderbook";

interface Props {
  configuredPairs: Record<Exchange, string[]>;
  onAdd: (exchange: Exchange, pair: string) => void;
}

export function RowConfigPanel({ configuredPairs, onAdd }: Props) {
  const [exchange, setExchange] = useState<Exchange>("okx");
  const [pair, setPair] = useState(EXCHANGE_SYMBOLS[exchange][0]);

  const handleExchangeChange = (ex: Exchange) => {
    setExchange(ex);
    setPair(EXCHANGE_SYMBOLS[ex][0]);
  };

  const alreadyAdded = configuredPairs[exchange]?.includes(pair);

  return (
    <div className="flex items-center gap-3 px-6 py-3 bg-white/[0.02] border-b border-white/10">
      <select
        value={exchange}
        onChange={(e) => handleExchangeChange(e.target.value as Exchange)}
        className="px-3 py-1.5 text-sm rounded-lg border border-white/20 bg-white/5 text-white cursor-pointer outline-none hover:border-white/30 focus:border-blue-500"
      >
        <option value="kraken">Kraken</option>
        <option value="okx">OKX</option>
      </select>

      <select
        value={pair}
        onChange={(e) => setPair(e.target.value)}
        className="px-3 py-1.5 text-sm rounded-lg border border-white/20 bg-white/5 text-white cursor-pointer outline-none hover:border-white/30 focus:border-blue-500"
      >
        {EXCHANGE_SYMBOLS[exchange].map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <button
        onClick={() => onAdd(exchange, pair)}
        disabled={alreadyAdded}
        className="px-4 py-1.5 text-sm font-medium rounded-lg transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed bg-blue-600 text-white hover:bg-blue-500"
      >
        {alreadyAdded ? "Added" : "Add Pair"}
      </button>
    </div>
  );
}
