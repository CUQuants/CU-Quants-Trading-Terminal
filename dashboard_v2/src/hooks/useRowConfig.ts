import { useState, useCallback } from "react";
import type { Exchange } from "../types/orderbook";

const STORAGE_KEY = "terminal_bear_config";
const CONFIG_VERSION = 1;

export interface RowConfig {
  version: number;
  exchanges: Record<Exchange, string[]>;
}

const DEFAULT_CONFIG: RowConfig = {
  version: CONFIG_VERSION,
  exchanges: {
    kraken: [],
    okx: [],
    gemini: [],
  },
};

function loadConfig(): RowConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_CONFIG;
    const parsed = JSON.parse(raw) as RowConfig;
    if (parsed.version !== CONFIG_VERSION) return DEFAULT_CONFIG;
    return parsed;
  } catch {
    return DEFAULT_CONFIG;
  }
}

function saveConfig(config: RowConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function useRowConfig() {
  const [config, setConfig] = useState<RowConfig>(loadConfig);

  const addPair = useCallback((exchange: Exchange, pair: string) => {
    setConfig((prev) => {
      if (prev.exchanges[exchange].includes(pair)) return prev;
      const next: RowConfig = {
        ...prev,
        exchanges: {
          ...prev.exchanges,
          [exchange]: [...prev.exchanges[exchange], pair],
        },
      };
      saveConfig(next);
      return next;
    });
  }, []);

  const removePair = useCallback((exchange: Exchange, pair: string) => {
    setConfig((prev) => {
      const next: RowConfig = {
        ...prev,
        exchanges: {
          ...prev.exchanges,
          [exchange]: prev.exchanges[exchange].filter((p) => p !== pair),
        },
      };
      saveConfig(next);
      return next;
    });
  }, []);

  return { config, addPair, removePair } as const;
}
