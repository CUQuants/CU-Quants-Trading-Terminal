/**
 * RMU Core's PnL report (GET /v1/pnl), passed through unchanged by the
 * gateway (POST /v1/rmu/pnl) and the terminal backend (GET /pnl).
 * Decimal amounts are strings so no precision is lost on the way.
 */
export interface PnlGroup {
  key: string;
  venue: string;
  market: string;
  base: string;
  quote_ccy: string;
  opened: boolean;
  opened_at: string | null;
  feed_down: string | null;
  bid: string | null;
  ask: string | null;
  mark: string | null;
  mark_as_of: string | null;
  mark_age_s: number | null;
  mark_error: string | null;
  fills: number;
  position: string;
  avg_cost: string;
  realized: string;
  fees: string;
  unrealized: string | null;
  pnl: string | null;
  nav: string | null;
  unconverted_fees: Record<string, string>;
}

export interface PnlTotals {
  realized: string;
  unrealized: string | null;
  fees: string;
  pnl: string | null;
  complete: boolean;
}

export interface PnlReport {
  as_of: string;
  group_by: string;
  pair_pnl: { running: boolean; error: string | null; untracked: string[] };
  groups: PnlGroup[];
  totals: Record<string, PnlTotals>;
  total: { ccy: string; pnl: string | null; complete: boolean; missing: string[] } | null;
  portfolio: {
    quote_ccy: string;
    nav: string | null;
    complete: boolean;
    as_of: string | null;
    by_venue: Record<string, string>;
    unpriced: string[];
  } | null;
}
