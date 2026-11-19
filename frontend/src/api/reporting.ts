import type {
  AuthFailure,
  LogFilters,
  LogHealth,
  LogPage,
  UnresolvedOrder,
} from "../types/reporting";
import { request } from "./client";


export function fetchLogHealth(): Promise<LogHealth> {
  return request(`/reporting/health`);
}

export function fetchUnresolvedOrders(): Promise<UnresolvedOrder[]> {
  return request(`/reporting/unresolved`);
}

export function fetchAuthFailures(): Promise<AuthFailure[]> {
  return request(`/reporting/auth-failures`);
}

export function fetchLogs(filters: LogFilters): Promise<LogPage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return request(`/reporting/logs${qs ? `?${qs}` : ""}`);
}
