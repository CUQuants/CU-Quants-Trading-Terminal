interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
}

export function FilterToggle<T extends string>({
  options,
  value,
  onChange,
}: Props<T>) {
  return (
    <div className="flex rounded-md overflow-hidden border border-white/10">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`cursor-pointer px-2.5 py-1 text-xs transition-colors ${
            value === opt.value
              ? "bg-white/10 text-white"
              : "text-white/40 hover:text-white/60"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
