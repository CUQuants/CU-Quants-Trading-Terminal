import type { Trade } from "../types/trades";
import { formatNum, formatTime, capitalize } from "../utils/format";
import { SortHeader } from "./ui/SortHeader";

export type SortKey =
  | "timestamp"
  | "exchange"
  | "pair"
  | "side"
  | "price"
  | "size"
  | "notional"
  | "fee"
  | "role";

export type SortDir = "asc" | "desc";

interface Props {
  trades: Trade[];
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
}

function notional(t: Trade) {
  return t.price * t.size;
}

export function TradesTable({ trades, sortKey, sortDir, onSort }: Props) {
  const shared = { currentKey: sortKey, currentDir: sortDir, onSort };

  if (trades.length === 0) {
    return (
      <div className="flex items-center justify-center py-24 text-white/30">
        No trades found.
      </div>
    );
  }

  return (
    <table className="w-full text-xs table-fixed">
      <colgroup>
        <col className="w-[15%]" /> {/* Time */}
        <col className="w-[7%]" />  {/* Exchange */}
        <col className="w-[7%]" />  {/* Pair */}
        <col className="w-[5%]" />  {/* Side */}
        <col className="w-[12%]" /> {/* Price */}
        <col className="w-[10%]" /> {/* Size */}
        <col className="w-[12%]" /> {/* Notional */}
        <col className="w-[20%]" /> {/* Fee */}
        <col className="w-[12%]" /> {/* Role */}
      </colgroup>
      <thead>
        <tr className="text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
          <th className="px-3 py-2 text-left font-medium">
            <SortHeader label="Time" sortKey="timestamp" {...shared} />
          </th>
          <th className="px-3 py-2 text-left font-medium">
            <SortHeader label="Exchange" sortKey="exchange" {...shared} />
          </th>
          <th className="px-3 py-2 text-left font-medium">
            <SortHeader label="Pair" sortKey="pair" {...shared} />
          </th>
          <th className="px-3 py-2 text-left font-medium">
            <SortHeader label="Side" sortKey="side" {...shared} />
          </th>
          <th className="px-3 py-2 text-right font-medium">
            <SortHeader label="Price" sortKey="price" {...shared} className="justify-end" />
          </th>
          <th className="px-3 py-2 text-right font-medium">
            <SortHeader label="Size" sortKey="size" {...shared} className="justify-end" />
          </th>
          <th className="px-3 py-2 text-right font-medium">
            <SortHeader label="Notional" sortKey="notional" {...shared} className="justify-end" />
          </th>
          <th className="px-3 py-2 text-right font-medium">
            <SortHeader label="Fee" sortKey="fee" {...shared} className="justify-end" />
          </th>
          <th className="px-3 py-2 text-left font-medium">
            <SortHeader label="Role" sortKey="role" {...shared} />
          </th>
        </tr>
      </thead>
      <tbody>
        {trades.map((t) => (
          <tr
            key={`${t.exchange}-${t.id}`}
            className="border-b border-white/5 hover:bg-white/[0.03] transition-colors"
          >
            <td className="px-3 py-2 text-white/50 tabular-nums truncate">
              {formatTime(t.timestamp)}
            </td>
            <td className="px-3 py-2 text-white/60 truncate">{capitalize(t.exchange)}</td>
            <td className="px-3 py-2 font-medium truncate">{t.pair}</td>
            <td className="px-3 py-2">
              <span
                className={
                  t.side === "buy" ? "text-emerald-400" : "text-red-400"
                }
              >
                {t.side.toUpperCase()}
              </span>
            </td>
            <td className="px-3 py-2 text-right tabular-nums">
              {formatNum(t.price, t.price < 1 ? 6 : 2)}
            </td>
            <td className="px-3 py-2 text-right tabular-nums">
              {formatNum(t.size, 6)}
            </td>
            <td className="px-3 py-2 text-right tabular-nums text-white/70">
              ${formatNum(notional(t))}
            </td>
            <td className="px-3 py-2 text-right tabular-nums text-white/50 truncate">
              {formatNum(t.fee, 6)} {t.fee_currency}
            </td>
            <td className="px-3 py-2">
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wide ${
                  t.role === "maker"
                    ? "bg-blue-500/15 text-blue-400"
                    : "bg-amber-500/15 text-amber-400"
                }`}
              >
                {t.role}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
