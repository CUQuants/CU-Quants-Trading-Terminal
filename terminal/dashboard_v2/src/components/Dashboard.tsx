import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Exchange } from "../types/orderbook";
import type { RowConfig } from "../hooks/useRowConfig";
import { useOkxWs } from "../contexts/OkxWsContext";
import { useKrakenWs } from "../contexts/KrakenWsContext";
import { DashboardHeader } from "./DashboardHeader";
import { RowConfigPanel } from "./RowConfigPanel";
import { TickerRow } from "./TickerRow";
import { OrderPanel } from "./OrderPanel";

interface Props {
  config: RowConfig;
  onAddPair: (exchange: Exchange, pair: string) => void;
  onRemovePair: (exchange: Exchange, pair: string) => void;
}

interface SelectedTicker {
  exchange: Exchange;
  pair: string;
}

export function Dashboard({ config, onAddPair, onRemovePair }: Props) {
  const queryClient = useQueryClient();
  const okxWs = useOkxWs();
  const krakenWs = useKrakenWs();
  const [selected, setSelected] = useState<SelectedTicker | null>(null);

  // Sync WS subscriptions with row config on mount
  useEffect(() => {
    for (const pair of config.exchanges.okx) okxWs.subscribe(pair);
    for (const pair of config.exchanges.kraken) krakenWs.subscribe(pair);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleAdd(exchange: Exchange, pair: string) {
    onAddPair(exchange, pair);
    if (exchange === "okx") okxWs.subscribe(pair);
    else krakenWs.subscribe(pair);
  }

  function handleRemove(exchange: Exchange, pair: string) {
    onRemovePair(exchange, pair);
    if (exchange === "okx") okxWs.unsubscribe(pair);
    else krakenWs.unsubscribe(pair);
    queryClient.removeQueries({ queryKey: ["orders", exchange, pair] });

    if (selected?.exchange === exchange && selected?.pair === pair) {
      setSelected(null);
    }
  }

  const allTickers: SelectedTicker[] = [
    ...config.exchanges.kraken.map((pair) => ({
      exchange: "kraken" as Exchange,
      pair,
    })),
    ...config.exchanges.okx.map((pair) => ({
      exchange: "okx" as Exchange,
      pair,
    })),
  ];

  function getOrderbook(exchange: Exchange, pair: string) {
    return exchange === "okx"
      ? okxWs.orderbook[pair]
      : krakenWs.orderbook[pair];
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <DashboardHeader />

      <RowConfigPanel
        configuredPairs={config.exchanges}
        onAdd={handleAdd}
      />

      {/* Ticker table */}
      <main className="flex-1">
        {allTickers.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-white/30">
            <p className="text-lg mb-2">No pairs configured</p>
            <p className="text-sm">
              Use the controls above to add an exchange/pair to get started.
            </p>
          </div>
        ) : (
          <>
            {/* Table header */}
            <div className="flex items-center gap-4 px-5 py-2 text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
              <span className="w-14">Exch</span>
              <span className="w-24">Pair</span>
              <span className="w-28 text-right">Bid</span>
              <span className="w-28 text-right">Ask</span>
              <span className="w-28 text-right">Spread</span>
              <span className="ml-auto" />
            </div>

            {allTickers.map(({ exchange, pair }) => (
              <TickerRow
                key={`${exchange}-${pair}`}
                exchange={exchange}
                pair={pair}
                orderbook={getOrderbook(exchange, pair)}
                isSelected={
                  selected?.exchange === exchange && selected?.pair === pair
                }
                onClick={() => setSelected({ exchange, pair })}
                onRemove={() => handleRemove(exchange, pair)}
              />
            ))}
          </>
        )}
      </main>

      {/* Order panel overlay */}
      {selected && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-40"
            onClick={() => setSelected(null)}
          />
          <OrderPanel
            exchange={selected.exchange}
            pair={selected.pair}
            orderbook={getOrderbook(selected.exchange, selected.pair)}
            onClose={() => setSelected(null)}
          />
        </>
      )}
    </div>
  );
}
