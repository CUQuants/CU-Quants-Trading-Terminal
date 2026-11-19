import { apiFetch, ApiError } from "./client";

export interface Operator {
  operator_id: string;
  operator_name: string;
}

export interface Credentials {
  api_key: string;
  api_secret: string;
  operator_id: string;
  operator_name: string;
}

export type CredentialField = keyof Credentials;

/** A sign-in the backend refused, with what it said about why. */
export class LoginError extends ApiError {
  field?: CredentialField;
  requestId?: string;

  constructor(message: string, status: number, field?: CredentialField, requestId?: string) {
    super(message, status);
    this.name = "LoginError";
    this.field = field;
    this.requestId = requestId;
  }
}

/** The signed-in operator, or null when there is no live session. */
export async function fetchMe(): Promise<Operator | null> {
  const res = await apiFetch("/auth/me");
  if (res.status === 401) return null;
  if (!res.ok) throw new ApiError(`Request failed: ${res.status}`, res.status);
  return res.json();
}

export async function login(creds: Credentials): Promise<Operator> {
  let res: Response;
  try {
    res = await apiFetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(creds),
    });
  } catch {
    throw new LoginError("Can't reach the terminal server.", 0);
  }
  if (res.ok) return res.json();

  let message = `Sign-in failed (${res.status}).`;
  let field: CredentialField | undefined;
  let requestId: string | undefined;
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") {
      message = detail;
    } else if (detail && typeof detail === "object") {
      if (detail.message) message = String(detail.message);
      field = detail.field;
      requestId = detail.request_id;
    }
  } catch {
    /* non-JSON error body: keep the status message */
  }
  throw new LoginError(message, res.status, field, requestId);
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" }).catch(() => undefined);
}
