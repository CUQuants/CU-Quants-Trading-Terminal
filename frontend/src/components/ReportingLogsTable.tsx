import { Fragment, useState } from "react";
import type { LogEntry } from "../types/reporting";

interface Props {
  logs: LogEntry[];
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}

function statusColor(entry: LogEntry): string {
  if (entry.error_code) return "text-red-400";
  if (entry.http_status && entry.http_status >= 400) return "text-red-400";
  return "text-emerald-400";
}

export function ReportingLogsTable({ logs }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (logs.length === 0) {
    return (
      <div className="flex items-center justify-center py-24 text-white/30">
        No log entries found.
      </div>
    );
  }

  return (
    <table className="w-full text-xs table-fixed">
      <colgroup>
        <col className="w-[14%]" /> {/* Time */}
        <col className="w-[12%]" /> {/* Operator */}
        <col className="w-[8%]" />  {/* Exchange */}
        <col className="w-[12%]" /> {/* Action */}
        <col className="w-[10%]" /> {/* Status */}
        <col className="w-[10%]" /> {/* Error */}
        <col className="w-[8%]" />  {/* Latency */}
        <col className="w-[12%]" /> {/* Source IP */}
        <col className="w-[14%]" /> {/* Request ID */}
      </colgroup>
      <thead>
        <tr className="text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
          <th className="px-3 py-2 text-left font-medium">Time</th>
          <th className="px-3 py-2 text-left font-medium">Operator</th>
          <th className="px-3 py-2 text-left font-medium">Exchange</th>
          <th className="px-3 py-2 text-left font-medium">Action</th>
          <th className="px-3 py-2 text-left font-medium">Status</th>
          <th className="px-3 py-2 text-left font-medium">Error</th>
          <th className="px-3 py-2 text-right font-medium">Latency</th>
          <th className="px-3 py-2 text-left font-medium">Source IP</th>
          <th className="px-3 py-2 text-left font-medium">Request ID</th>
        </tr>
      </thead>
      <tbody>
        {logs.map((entry) => {
          const isExpanded = expanded === entry.request_id;
          return (
            <Fragment key={entry.request_id}>
              <tr
                onClick={() =>
                  setExpanded(isExpanded ? null : entry.request_id)
                }
                className="border-b border-white/5 hover:bg-white/[0.03] transition-colors cursor-pointer"
              >
                <td className="px-3 py-2 text-white/50 tabular-nums truncate">
                  {formatTimestamp(entry.timestamp)}
                </td>
                <td className="px-3 py-2 truncate">
                  {entry.operator_name || entry.system_name || "—"}
                </td>
                <td className="px-3 py-2 text-white/60 truncate">
                  {entry.exchange || "—"}
                </td>
                <td className="px-3 py-2 font-medium truncate">{entry.action}</td>
                <td className={`px-3 py-2 truncate ${statusColor(entry)}`}>
                  {entry.response_status || entry.http_status || "—"}
                </td>
                <td className="px-3 py-2 text-red-400/80 truncate">
                  {entry.error_code || "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-white/50">
                  {entry.latency_ms != null ? `${entry.latency_ms}ms` : "—"}
                </td>
                <td className="px-3 py-2 text-white/40 truncate">
                  {entry.source_ip || "—"}
                </td>
                <td className="px-3 py-2 text-white/30 truncate">
                  {entry.request_id}
                </td>
              </tr>
              {isExpanded && (
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <td colSpan={9} className="px-3 py-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-[10px] uppercase tracking-widest text-white/30 mb-1">
                          Request payload
                        </div>
                        <pre className="whitespace-pre-wrap break-all text-white/60 text-[11px]">
                          {JSON.stringify(entry.request_payload, null, 2) ?? "—"}
                        </pre>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-widest text-white/30 mb-1">
                          Response summary
                        </div>
                        <pre className="whitespace-pre-wrap break-all text-white/60 text-[11px]">
                          {JSON.stringify(entry.response_summary, null, 2) ?? "—"}
                        </pre>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
