export interface LogHealth {
  months_of_runway: number;
  default_partition_rows: number;
  unprotected_partitions: number;
  rows_last_24h: number;
  newest_row: string | null;
  max_clock_skew_sec: number | null;
}

export interface UnresolvedOrder {
  request_id: string;
  timestamp: string;
  operator_id: string | null;
  operator_name: string | null;
  system_name: string | null;
  exchange: string | null;
  action: string;
  source_ip: string | null;
  unresolved_for: string;
}

export interface AuthFailure {
  api_key_id: string | null;
  source_ip: string | null;
  failures: number;
  latest: string;
}

export interface LogEntry {
  request_id: string;
  action: string;
  response_status: string | null;
  timestamp: string;
  operator_id: string | null;
  operator_name: string | null;
  system_name: string | null;
  exchange: string | null;
  request_payload: unknown;
  response_summary: unknown;
  latency_ms: number | null;
  source_ip: string | null;
  order_id: string | null;
  http_status: number | null;
  error_code: string | null;
  api_key_id: string | null;
}

export interface LogPage {
  logs: LogEntry[];
  next_cursor: string | null;
}

export interface LogFilters {
  since?: string;
  until?: string;
  operator_id?: string;
  operator_name?: string;
  exchange?: string;
  action?: string;
  response_status?: string;
  error_code?: string;
  api_key_id?: string;
  source_ip?: string;
  request_id?: string;
  limit?: number;
  cursor?: string;
}
