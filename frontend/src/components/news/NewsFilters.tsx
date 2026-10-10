import { useState } from "react";
import type { NewsStatus, NewsViewState } from "../../types/news";

interface Props {
  state: NewsViewState;
  configuredPairs: string[];
  status?: NewsStatus;
  onChange: (state: NewsViewState) => void;
}

const selectClass = "h-10 min-w-0 w-full rounded-md border border-white/15 bg-[#111] px-3 py-2 text-sm text-white/80 focus:outline-none focus:border-sky-400/60";

export function NewsFilters({ state, configuredPairs, status, onChange }: Props) {
  const [expanded, setExpanded] = useState(false);
  const categories = status?.categories ?? [];
  const sources = status?.sources ?? [];
  const selectedPairs = state.selectedPairs.filter((pair) => configuredPairs.includes(pair));

  return (
    <div className="relative order-3 col-span-2 min-w-0 flex-1 min-[1800px]:order-none">
      <button type="button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}
        className="rounded border border-white/15 px-3 py-1.5 text-xs text-white/75 cursor-pointer min-[1800px]:hidden">
        Filters · {state.mode === "articles" ? "Articles" : "Grouped events"}
      </button>
      <div className={`${expanded ? "block" : "hidden"} absolute inset-x-0 top-full z-30 mt-2 max-h-[60vh] overflow-y-auto rounded-lg border border-white/15 bg-[#111] p-4 shadow-xl min-[1800px]:static min-[1800px]:block min-[1800px]:m-0 min-[1800px]:max-h-none min-[1800px]:overflow-visible min-[1800px]:border-0 min-[1800px]:bg-transparent min-[1800px]:p-0 min-[1800px]:shadow-none`}>
      <div className="grid grid-cols-2 items-center gap-x-3 gap-y-7 pt-4 min-[1800px]:flex min-[1800px]:gap-3 min-[1800px]:pt-0 [&>label]:min-w-0">
        <div className="col-span-2 flex h-10 shrink-0 w-fit rounded-md border border-white/15 p-1 gap-1" role="group" aria-label="News display">
          {(["articles", "events"] as const).map((mode) => (
            <button key={mode} type="button" aria-pressed={state.mode === mode} onClick={() => onChange({ ...state, mode })}
              className={`rounded px-3 text-sm whitespace-nowrap cursor-pointer ${state.mode === mode ? "bg-white/10 text-white" : "text-white/50 hover:text-white/80"}`}>
              {mode === "events" ? "Grouped events" : "Articles"}
            </button>
          ))}
        </div>
        <label className="relative flex text-xs text-white/50">
          <span className="absolute bottom-full mb-1">Category</span>
          <select value={state.category ?? ""} onChange={(e) => onChange({ ...state, category: e.target.value || null })} className={selectClass}>
            <option value="">All categories</option>
            {state.category && !categories.some((category) => category.id === state.category) && <option value={state.category}>{state.category}</option>}
            {categories.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}
          </select>
        </label>
        <label className="relative flex text-xs text-white/50">
          <span className="absolute bottom-full mb-1">Source</span>
          <select value={state.source ?? ""} onChange={(e) => onChange({ ...state, source: e.target.value || null })} className={selectClass}>
            <option value="">All sources</option>
            {state.source && !sources.some((source) => source.id === state.source) && <option value={state.source}>{state.source}</option>}
            {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
          </select>
        </label>
        <label className="relative flex text-xs text-white/50">
          <span className="absolute bottom-full mb-1">Timeframe</span>
          <select value={state.timeframe} onChange={(e) => onChange({ ...state, timeframe: e.target.value as NewsViewState["timeframe"] })} className={selectClass}>
            <option value="1h">Last hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
          </select>
        </label>
        <label className="relative flex text-xs text-white/50">
          <span className="absolute bottom-full mb-1 whitespace-nowrap">Pair coverage</span>
          <select value={configuredPairs.length === 0 ? "all" : state.pairScope}
            onChange={(e) => onChange({
              ...state,
              pairScope: e.target.value as NewsViewState["pairScope"],
              selectedPairs: e.target.value === "selected" && selectedPairs.length === 0 ? configuredPairs : state.selectedPairs,
            })} className={selectClass}>
            <option value="configured" disabled={configuredPairs.length === 0}>All configured pairs</option>
            <option value="selected" disabled={configuredPairs.length === 0}>Choose configured pairs</option>
            <option value="all">All news</option>
          </select>
        </label>
        <label className="relative flex text-xs text-white/50">
          <span className="absolute bottom-full mb-1">Assets</span>
          <input type="text" value={state.assetQuery} placeholder="BTC, ETH, AAPL"
            onChange={(e) => onChange({ ...state, assetQuery: e.target.value })}
            className={selectClass} />
        </label>
      </div>
      {configuredPairs.length > 0 && state.pairScope === "selected" ? (
        <fieldset className="flex flex-wrap gap-3 py-2">
          <legend className="text-xs text-white/50 mb-2">Select configured pairs</legend>
          {configuredPairs.map((pair) => (
            <label key={pair} className="flex items-center gap-2 text-xs text-white/75 cursor-pointer">
              <input type="checkbox" checked={selectedPairs.includes(pair)} className="accent-sky-400"
                onChange={(e) => onChange({ ...state, selectedPairs: e.target.checked ? [...selectedPairs, pair] : selectedPairs.filter((item) => item !== pair) })} />
              {pair}
            </label>
          ))}
        </fieldset>
      ) : null}
      </div>
    </div>
  );
}
