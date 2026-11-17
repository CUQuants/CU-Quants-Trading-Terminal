/**
 * Format a number with locale-aware grouping and fixed decimal places.
 * Used across orderbook rows, ticker rows, trade tables, etc.
 */
export function formatNum(n: number, decimals = 4): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

const tradeTimeFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Denver",
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZoneName: "short",
});

export function formatTime(ts: string): string {
  if (!ts.trim()) return "—";
  const ms = Number(ts);
  if (!Number.isFinite(ms)) return "—";
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return "—";
  return tradeTimeFormatter.format(date);
}

/** Uppercase the first letter of a string. */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
