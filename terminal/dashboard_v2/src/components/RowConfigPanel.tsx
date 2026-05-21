import { useState, type KeyboardEvent, type ChangeEvent } from "react";
import type { Exchange } from "../types/orderbook";
import type { ExchangePairOptions } from "../hooks/useRowConfig";

const PAIR_PATTERN = /^[A-Z0-9]+\/[A-Z0-9]+$/i;

function normalizePair(input: string): string {
  return input.trim().toUpperCase();
}

function isValidPair(input: string): boolean {
  return PAIR_PATTERN.test(normalizePair(input));
}

interface Props {
  configuredPairs: Record<Exchange, string[]>;
  pairOptions: ExchangePairOptions;
  onAdd: (exchange: Exchange, pair: string) => void;
}

export function RowConfigPanel({ configuredPairs, pairOptions, onAdd }: Props) {
  const [exchange, setExchange] = useState<Exchange>("okx");
  const [pairInput, setPairInput] = useState("");

  const pair = normalizePair(pairInput);
  const isValid = pair.length > 0 && isValidPair(pairInput);
  const alreadyAdded = isValid && configuredPairs[exchange]?.includes(pair);

  const handleAdd = () => {
    if (!isValid || alreadyAdded) return;
    onAdd(exchange, pair);
    setPairInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleAdd();
  };

  const handleExchangeChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setExchange(e.target.value as Exchange);
  };

  const handlePairChange = (e: ChangeEvent<HTMLInputElement>) => {
    setPairInput(e.target.value);
  };

  return (
    <div className="flex items-center gap-3 px-6 py-3 bg-white/[0.02] border-b border-white/10">
      <select
        value={exchange}
        onChange={handleExchangeChange}
        className="px-3 py-1.5 text-sm rounded-lg border border-white/20 bg-white/5 text-white cursor-pointer outline-none hover:border-white/30 focus:border-blue-500"
      >
        <option value="kraken">Kraken</option>
        <option value="okx">OKX</option>
        <option value="gemini">Gemini</option>
      </select>

      <div className="relative flex-1 max-w-[200px]">
        <input
          type="text"
          value={pairInput}
          onChange={handlePairChange}
          onKeyDown={handleKeyDown}
          placeholder="e.g. BTC/USD or DOGE/USD"
          list="pair-suggestions"
          className="w-full px-3 py-1.5 text-sm rounded-lg border border-white/20 bg-white/5 text-white placeholder-white/30 outline-none hover:border-white/30 focus:border-blue-500"
        />
        <datalist id="pair-suggestions">
          {pairOptions[exchange].map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </div>

      <button
        onClick={handleAdd}
        disabled={!isValid || alreadyAdded}
        className="px-4 py-1.5 text-sm font-medium rounded-lg transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed bg-blue-600 text-white hover:bg-blue-500"
      >
        {alreadyAdded ? "Added" : "Add Pair"}
      </button>
    </div>
  );
}
