import type { PnlReport } from "../types/pnl";
import { ApiError } from "./orders";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchPnl(): Promise<PnlReport> {
  const res = await fetch(`${API_BASE}/pnl`);
  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) message = String(body.detail);
    } catch {
      /* non-JSON error body: keep the status message */
    }
    throw new ApiError(message, res.status);
  }
  return res.json();
}
