import type { RiskStatus } from "../types/risk";
import { ApiError, apiFetch } from "./client";

export async function fetchRiskStatus(): Promise<RiskStatus> {
  const res = await apiFetch("/risk");
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
