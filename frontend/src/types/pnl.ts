/**
 * RMU Core's PnL report (GET /v1/pnl), passed through unchanged by the
 * gateway (POST /v1/rmu/pnl) and the terminal backend (GET /pnl).
 * Decimal amounts are strings so no precision is lost on the way.
 */
/** Fills on one side since the pair opened: size-weighted average price. */
export interface PnlTradedSide {
  qty: string;
  avg_px: string | null;
}

/** Every fill since the pair opened, by side, and the spread between them. */
export interface PnlTraded {
  buy: PnlTradedSide;
  sell: PnlTradedSide;
  /** The smaller of buy and sell qty: what `spread` was earned on. */
  matched_qty: string;
  /** sell avg_px − buy avg_px; null until both sides have traded. */
  spread: string | null;
  spread_bps: string | null;
}

/** Open orders resting on one side: unfilled size and its weighted limit price. */
export interface PnlOpenSide {
  qty: string;
  avg_px: string | null;
  count: number;
  /** Open orders with no limit price, left out of qty and avg_px. */
  unpriced: number;
}

export interface PnlOpenOrders {
  /** False while the venue's open-order list may be stale. */
  ready: boolean;
  buy: PnlOpenSide;
  sell: PnlOpenSide;
}

/** Position and break-even if every open order on that side filled at its limit. */
export interface PnlProjection {
  position: string;
  avg_cost: string;
}

export interface PnlProjected {
  /** Only when long or flat (buys grow the position). */
  if_buys_fill: PnlProjection | null;
  /** Only when short or flat. */
  if_sells_fill: PnlProjection | null;
}

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
  // Absent on an RMU older than the open-order-average change; null when not
  // computable (pair not loaded, no order ledger, open orders not ready).
  traded?: PnlTraded | null;
  open_orders?: PnlOpenOrders | null;
  projected?: PnlProjected | null;
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
