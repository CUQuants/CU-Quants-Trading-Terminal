import type { PnlReport } from "../types/pnl";
import { ApiError, apiFetch } from "./client";

export async function fetchPnl(): Promise<PnlReport> {
  const res = await apiFetch("/pnl");
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
