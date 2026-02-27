import { useMemo } from "react";
import { Toaster } from "react-hot-toast";
import type { Exchange } from "./types/orderbook";
import { useRowConfig } from "./hooks/useRowConfig";
import { OkxWsProvider } from "./contexts/OkxWsContext";
import { KrakenWsProvider } from "./contexts/KrakenWsContext";
import { OrderEventsProvider } from "./contexts/OrderEventsContext";
import { ActiveOrdersProvider } from "./contexts/ActiveOrdersContext";
import { Dashboard } from "./components/Dashboard";

function App() {
  const { config, addPair, removePair } = useRowConfig();

  const activeExchanges = useMemo<Exchange[]>(() => {
    const result: Exchange[] = [];
    if (config.exchanges.kraken.length > 0) result.push("kraken");
    if (config.exchanges.okx.length > 0) result.push("okx");
    return result;
  }, [config.exchanges.kraken.length, config.exchanges.okx.length]);

  return (
    <OrderEventsProvider activeExchanges={activeExchanges}>
      <KrakenWsProvider>
        <OkxWsProvider>
          <ActiveOrdersProvider configuredPairs={config.exchanges}>
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: "#1a1a1a",
                  color: "#fff",
                  border: "1px solid rgba(255,255,255,0.1)",
                  fontSize: "14px",
                },
              }}
            />
            <Dashboard
              config={config}
              onAddPair={addPair}
              onRemovePair={removePair}
            />
          </ActiveOrdersProvider>
        </OkxWsProvider>
      </KrakenWsProvider>
    </OrderEventsProvider>
  );
}

export default App;
