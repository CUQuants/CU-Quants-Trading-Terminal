import { useMemo, useState } from "react";
import { Toaster } from "react-hot-toast";
import type { Exchange } from "./types/orderbook";
import { useRowConfig } from "./hooks/useRowConfig";
import { OkxWsProvider } from "./contexts/OkxWsContext";
import { KrakenWsProvider } from "./contexts/KrakenWsContext";
import { GeminiWsProvider } from "./contexts/GeminiWsContext";
import { OrderEventsProvider } from "./contexts/OrderEventsContext";
import { ActiveOrdersProvider } from "./contexts/ActiveOrdersContext";
import { DashboardHeader, type View } from "./components/DashboardHeader";
import { Dashboard } from "./components/Dashboard";
import { TradesView } from "./components/TradesView";
import { AccountView } from "./components/AccountView";

function App() {
  const { config, addPair, removePair } = useRowConfig();
  const [currentView, setCurrentView] = useState<View>("dashboard");

  const activeExchanges = useMemo<Exchange[]>(() => {
    const result: Exchange[] = [];
    if (config.exchanges.kraken.length > 0) result.push("kraken");
    if (config.exchanges.okx.length > 0) result.push("okx");
    if (config.exchanges.gemini.length > 0) result.push("gemini");
    return result;
  }, [config.exchanges.kraken?.length, config.exchanges.okx?.length, config.exchanges.gemini?.length]);

  return (
    <OrderEventsProvider activeExchanges={activeExchanges}>
      <KrakenWsProvider>
        <OkxWsProvider>
          <GeminiWsProvider>
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
            <div className="min-h-screen bg-black text-white flex flex-col">
              <DashboardHeader
                currentView={currentView}
                onViewChange={setCurrentView}
              />
              {currentView === "dashboard" && (
                <Dashboard
                  config={config}
                  onAddPair={addPair}
                  onRemovePair={removePair}
                />
              )}
              {currentView === "trades" && (
                <TradesView activeExchanges={activeExchanges} />
              )}
              {currentView === "account" && (
                <AccountView activeExchanges={activeExchanges} />
              )}
            </div>
          </ActiveOrdersProvider>
          </GeminiWsProvider>
        </OkxWsProvider>
      </KrakenWsProvider>
    </OrderEventsProvider>
  );
}

export default App;
