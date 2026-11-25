/**
 * RMU Core's risk status, via the gateway (POST /v1/rmu/risk) and the
 * terminal backend (GET /risk). Today: the PnL kill switch, exactly as the
 * RMU's GET /v1/kill-switch returns it. Decimal amounts are strings.
 */
export interface KillSwitchStatus {
  enabled: boolean;
  tripped: boolean;
  trip_reason: string | null;
  /** False: the trip holds in memory but couldn't be saved yet (RMU retries). */
  trip_persisted: boolean;
  /** NAV now − baseline NAV − net deposits/withdrawals since the baseline. */
  pnl: string | null;
  /** The loss that trips it, as a positive amount (tighter of absolute and %). */
  threshold: string | null;
  baseline_nav: string | null;
  baseline_ts: string | null;
  /** Where the baseline came from: "config", "stored", "first_sample" or "rebase". */
  baseline_source: string | null;
  baseline_persisted: boolean;
  nav: string | null;
  nav_as_of: string | null;
}

export interface RiskStatus {
  kill_switch: KillSwitchStatus;
}
