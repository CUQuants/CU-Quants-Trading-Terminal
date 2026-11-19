/**
 * The one place the frontend talks to the terminal backend.
 *
 * The backend is reached same-origin under `/api` — Caddy in production, the
 * Vite dev proxy locally — so the HttpOnly session cookie set at sign-in
 * rides along on every request and WebSocket handshake. Nothing auth-related
 * is ever stored in JS.
 */

export const API_BASE: string = (import.meta.env.VITE_API_URL ?? "/api").replace(/\/$/, "");

/** `ws(s)://` base for the backend, resolved against the page's own origin. */
export function wsBase(): string {
  const url = new URL(API_BASE || "/", window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString().replace(/\/$/, "");
}

/** Fired on any 401, so AuthContext can check whether the session is gone. */
export const AUTH_EXPIRED_EVENT = "auth:expired";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Raw fetch against the backend, with the session cookie and 401 signalling. */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "same-origin", ...init });
  if (res.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  return res;
}

/** JSON request; throws ApiError carrying the raw response body on failure. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(body || `Request failed: ${res.status}`, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
