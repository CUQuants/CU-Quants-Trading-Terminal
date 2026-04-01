import { useState, useCallback, useEffect } from "react";
import type { Exchange } from "../types/orderbook";
import { fetchExchangePairs } from "../api/pairs";

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

export type ExchangePairOptions = Record<Exchange, string[]>;

const DEFAULT_PAIR_OPTIONS: ExchangePairOptions = {
  kraken: [],
  okx: [],
  gemini: [],
};

function mergeUnique(base: string[], incoming: string[]): string[] {
  return [...new Set([...base, ...incoming])];
}

function normalizePair(input: string): string {
  return input.trim().toUpperCase();
}

function normalizeExchangePairs(
  input: Partial<Record<string, string[]>>,
): ExchangePairOptions {
  return {
    kraken: (input.kraken ?? []).map(normalizePair),
    okx: (input.okx ?? []).map(normalizePair),
    gemini: (input.gemini ?? []).map(normalizePair),
  };
}

export function useRowConfig() {
  const [config, setConfig] = useState<RowConfig>(DEFAULT_CONFIG);
  const [pairOptions, setPairOptions] =
    useState<ExchangePairOptions>(DEFAULT_PAIR_OPTIONS);

  useEffect(() => {
    let active = true;

    fetchExchangePairs()
      .then((pairsFromApi) => {
        if (!active) return;

        const normalized = normalizeExchangePairs(pairsFromApi);
        setPairOptions(normalized);
        setConfig((prev) => ({
          ...prev,
          exchanges: {
            kraken: mergeUnique(prev.exchanges.kraken, normalized.kraken),
            okx: mergeUnique(prev.exchanges.okx, normalized.okx),
            gemini: mergeUnique(prev.exchanges.gemini, normalized.gemini),
          },
        }));
      })
      .catch(() => {
        // Gracefully keep running with an empty/default config if API is unavailable.
      });

    return () => {
      active = false;
    };
  }, []);

  const addPair = useCallback((exchange: Exchange, pair: string) => {
    setConfig((prev) => {
      if (prev.exchanges[exchange].includes(pair)) return prev;
      return {
        ...prev,
        exchanges: {
          ...prev.exchanges,
          [exchange]: [...prev.exchanges[exchange], pair],
        },
      };
    });

    setPairOptions((prev) => ({
      ...prev,
      [exchange]: mergeUnique(prev[exchange], [pair]),
    }));
  }, []);

  const removePair = useCallback((exchange: Exchange, pair: string) => {
    setConfig((prev) => {
      return {
        ...prev,
        exchanges: {
          ...prev.exchanges,
          [exchange]: prev.exchanges[exchange].filter((p) => p !== pair),
        },
      };
    });
  }, []);

  return { config, pairOptions, addPair, removePair } as const;
}
