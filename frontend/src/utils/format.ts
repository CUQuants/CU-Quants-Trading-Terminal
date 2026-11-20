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

/**
 * Show an exact decimal string with every digit it carries: trailing zeros
 * after the point are dropped ("0.00100000" -> "0.001", "95000.10" ->
 * "95,000.1", "82.000" -> "82") and the integer part gets locale grouping.
 * Nothing is rounded. Unparseable input is returned unchanged.
 */
export function formatExact(s: string): string {
  const m = /^(-?)(\d+)(?:\.(\d*))?$/.exec(s.trim());
  if (!m) return s;
  const [, sign, int, frac = ""] = m;
  const trimmed = frac.replace(/0+$/, "");
  const grouped = BigInt(int).toLocaleString();
  return trimmed ? `${sign}${grouped}${DECIMAL_SEP}${trimmed}` : `${sign}${grouped}`;
}

const DECIMAL_SEP =
  new Intl.NumberFormat().formatToParts(1.1).find((p) => p.type === "decimal")?.value ?? ".";

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
