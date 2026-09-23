import type { NewsStatus, NewsViewState } from "../../types/news";

interface Props {
  state: NewsViewState;
  configuredPairs: string[];
  status?: NewsStatus;
  onChange: (state: NewsViewState) => void;
}

const selectClass = "rounded-md border border-white/15 bg-[#111] px-3 py-2 text-sm text-white/80 focus:outline-none focus:border-sky-400/60";

export function NewsFilters({ state, configuredPairs, status, onChange }: Props) {
  const categories = status?.categories ?? [];
  const sources = status?.sources ?? [];
  const selectedPairs = state.selectedPairs.filter((pair) => configuredPairs.includes(pair));

  return (
    <div className="space-y-3 border-y border-white/10 bg-white/[0.02] px-6 py-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex rounded-md border border-white/15 p-1 gap-1" role="group" aria-label="News display">
          {(["events", "articles"] as const).map((mode) => (
            <button key={mode} type="button" aria-pressed={state.mode === mode} onClick={() => onChange({ ...state, mode })}
              className={`rounded px-3 py-1.5 text-sm cursor-pointer ${state.mode === mode ? "bg-white/10 text-white" : "text-white/50 hover:text-white/80"}`}>
              {mode === "events" ? "Grouped events" : "Articles"}
            </button>
          ))}
        </div>
        <label className="flex flex-col gap-1 text-xs text-white/50">
          Category
          <select value={state.category ?? ""} onChange={(e) => onChange({ ...state, category: e.target.value || null })} className={selectClass}>
            <option value="">All categories</option>
            {state.category && !categories.some((category) => category.id === state.category) && <option value={state.category}>{state.category}</option>}
            {categories.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-white/50">
          Source
          <select value={state.source ?? ""} onChange={(e) => onChange({ ...state, source: e.target.value || null })} className={selectClass}>
            <option value="">All sources</option>
            {state.source && !sources.some((source) => source.id === state.source) && <option value={state.source}>{state.source}</option>}
            {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-white/50">
          Timeframe
          <select value={state.timeframe} onChange={(e) => onChange({ ...state, timeframe: e.target.value as NewsViewState["timeframe"] })} className={selectClass}>
            <option value="1h">Last hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-white/50">
          Pair coverage
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
      </div>
      {configuredPairs.length === 0 ? (
        <p className="text-xs text-white/45">No pairs configured. Showing all news; add pairs on the Dashboard to filter by your markets.</p>
      ) : state.pairScope === "selected" ? (
        <fieldset className="flex flex-wrap gap-3">
          <legend className="text-xs text-white/50 mb-2">Select configured pairs</legend>
          {configuredPairs.map((pair) => (
            <label key={pair} className="flex items-center gap-2 text-xs text-white/75 cursor-pointer">
              <input type="checkbox" checked={selectedPairs.includes(pair)} className="accent-sky-400"
                onChange={(e) => onChange({ ...state, selectedPairs: e.target.checked ? [...selectedPairs, pair] : selectedPairs.filter((item) => item !== pair) })} />
              {pair}
            </label>
          ))}
        </fieldset>
      ) : state.pairScope === "configured" ? (
        <p className="text-xs text-white/45">Matching configured pairs: {configuredPairs.join(", ")}</p>
      ) : null}
    </div>
  );
}
