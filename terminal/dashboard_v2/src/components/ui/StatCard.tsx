interface Props {
  label: string;
  value: string;
}

export function StatCard({ label, value }: Props) {
  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-lg px-4 py-3">
      <div className="text-[10px] uppercase tracking-widest text-white/30 mb-1">
        {label}
      </div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}
