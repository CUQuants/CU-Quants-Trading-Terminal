/**
 * Format a number with locale-aware grouping and fixed decimal places.
 * Used across orderbook rows, ticker rows, trade tables, etc.
 */
export function formatNum(n: number, decimals = 2): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format a millisecond-epoch timestamp string into a short human-readable form.
 * Falls back to the raw string if it can't be parsed as a number.
 */
export function formatTime(ts: string): string {
  const ms = Number(ts);
  if (isNaN(ms)) return ts;
  return new Date(ms).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Uppercase the first letter of a string. */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
