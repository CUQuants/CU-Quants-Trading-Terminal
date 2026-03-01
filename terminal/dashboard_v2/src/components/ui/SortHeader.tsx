interface Props<K extends string> {
  label: string;
  sortKey: K;
  currentKey: K;
  currentDir: "asc" | "desc";
  onSort: (key: K) => void;
  className?: string;
}

export function SortHeader<K extends string>({
  label,
  sortKey,
  currentKey,
  currentDir,
  onSort,
  className = "",
}: Props<K>) {
  const active = currentKey === sortKey;
  return (
    <button
      onClick={() => onSort(sortKey)}
      className={`w-full flex items-center gap-1 hover:text-white/70 transition-colors ${className}`}
    >
      {label}
      {active && (
        <span className="text-[10px]">{currentDir === "asc" ? "▲" : "▼"}</span>
      )}
    </button>
  );
}
