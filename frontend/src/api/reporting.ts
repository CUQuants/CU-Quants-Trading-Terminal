import type {
  AuthFailure,
  LogFilters,
  LogHealth,
  LogPage,
  UnresolvedOrder,
} from "../types/reporting";
import { ApiError } from "./orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(body || `Request failed: ${res.status}`, res.status);
  }
  return res.json() as Promise<T>;
}

export function fetchLogHealth(): Promise<LogHealth> {
  return request(`${API_BASE}/reporting/health`);
}

export function fetchUnresolvedOrders(): Promise<UnresolvedOrder[]> {
  return request(`${API_BASE}/reporting/unresolved`);
}

export function fetchAuthFailures(): Promise<AuthFailure[]> {
  return request(`${API_BASE}/reporting/auth-failures`);
}

export function fetchLogs(filters: LogFilters): Promise<LogPage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return request(`${API_BASE}/reporting/logs${qs ? `?${qs}` : ""}`);
}
