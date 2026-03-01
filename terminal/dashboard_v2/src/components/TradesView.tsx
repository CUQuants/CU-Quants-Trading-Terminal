import { useState, useMemo } from "react";
import type { Exchange } from "../types/orderbook";
import type { Trade } from "../types/trades";
import { formatNum, capitalize } from "../utils/format";
import { useTrades } from "../hooks/useTrades";
import { FilterToggle } from "./ui/FilterToggle";
import { StatCard } from "./ui/StatCard";
import { TradesTable, type SortKey, type SortDir } from "./TradesTable";

interface Filters {
  exchange: Exchange | "all";
  pair: string;
  side: "buy" | "sell" | "all";
  role: "maker" | "taker" | "all";
}

interface Props {
  activeExchanges: Exchange[];
}

function notional(t: Trade) {
  return t.price * t.size;
}

export function TradesView({ activeExchanges }: Props) {
  const { data: trades = [], isLoading, error, refetch } = useTrades(activeExchanges);

  const [filters, setFilters] = useState<Filters>({
    exchange: "all",
    pair: "all",
    side: "all",
    role: "all",
  });
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const availablePairs = useMemo(() => {
    const set = new Set(trades.map((t) => t.pair));
    return Array.from(set).sort();
  }, [trades]);

  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      if (filters.exchange !== "all" && t.exchange !== filters.exchange) return false;
      if (filters.pair !== "all" && t.pair !== filters.pair) return false;
      if (filters.side !== "all" && t.side !== filters.side) return false;
      if (filters.role !== "all" && t.role !== filters.role) return false;
      return true;
    });
  }, [trades, filters]);

  const sortedTrades = useMemo(() => {
    return [...filteredTrades].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "timestamp":
          cmp = Number(a.timestamp) - Number(b.timestamp);
          break;
        case "price":
        case "size":
        case "fee":
          cmp = a[sortKey] - b[sortKey];
          break;
        case "notional":
          cmp = notional(a) - notional(b);
          break;
        default:
          cmp = String(a[sortKey]).localeCompare(String(b[sortKey]));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filteredTrades, sortKey, sortDir]);

  const stats = useMemo(() => {
    const total = filteredTrades.length;
    const volume = filteredTrades.reduce((s, t) => s + notional(t), 0);
    const fees = filteredTrades.reduce((s, t) => s + t.fee, 0);
    const makers = filteredTrades.filter((t) => t.role === "maker").length;
    const makerPct = total > 0 ? (makers / total) * 100 : 0;
    return { total, volume, fees, makerPct };
  }, [filteredTrades]);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (activeExchanges.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-white/30">
        <p className="text-lg mb-2">No exchanges configured</p>
        <p className="text-sm">
          Switch to the Dashboard and add pairs to see trade history.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-3 px-6 py-4">
        <StatCard label="Trades" value={String(stats.total)} />
        <StatCard label="Volume" value={`$${formatNum(stats.volume)}`} />
        <StatCard label="Fees" value={`$${formatNum(stats.fees, 4)}`} />
        <StatCard label="Maker %" value={`${formatNum(stats.makerPct, 1)}%`} />
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-4 px-6 py-3 border-y border-white/10 bg-white/[0.02]">
        <FilterToggle
          value={filters.exchange}
          onChange={(v) => setFilters((f) => ({ ...f, exchange: v }))}
          options={[
            { value: "all" as const, label: "All" },
            ...activeExchanges.map((e) => ({ value: e, label: capitalize(e) })),
          ]}
        />

        <select
          value={filters.pair}
          onChange={(e) => setFilters((f) => ({ ...f, pair: e.target.value }))}
          className="bg-transparent border border-white/10 rounded-md px-2.5 py-1 text-xs text-white/80 outline-none focus:border-white/30"
        >
          <option value="all" className="bg-black">All Pairs</option>
          {availablePairs.map((p) => (
            <option key={p} value={p} className="bg-black">{p}</option>
          ))}
        </select>

        <FilterToggle
          value={filters.side}
          onChange={(v) => setFilters((f) => ({ ...f, side: v }))}
          options={[
            { value: "all" as const, label: "All" },
            { value: "buy" as const, label: "Buy" },
            { value: "sell" as const, label: "Sell" },
          ]}
        />

        <FilterToggle
          value={filters.role}
          onChange={(v) => setFilters((f) => ({ ...f, role: v }))}
          options={[
            { value: "all" as const, label: "All" },
            { value: "maker" as const, label: "Maker" },
            { value: "taker" as const, label: "Taker" },
          ]}
        />

        <div className="flex-1" />

        <button
          onClick={() => refetch()}
          className="text-xs text-white/40 hover:text-white/70 transition-colors border border-white/10 rounded-md px-3 py-1 cursor-pointer"
        >
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto px-6 py-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-24 text-white/30">
            <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mr-3" />
            Loading trades…
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-24 text-red-400/80">
            Failed to load trades: {(error as Error).message}
          </div>
        ) : (
          <TradesTable
            trades={sortedTrades}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
          />
        )}
      </div>
    </div>
  );
}
