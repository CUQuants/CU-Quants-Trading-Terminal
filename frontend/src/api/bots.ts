import type {
  BotFile,
  BotFileKind,
  BotFileSaved,
  BotStatus,
  LaunchMarketRequest,
  LaunchMarketResult,
} from "../types/bots";
import { ApiError, apiFetch } from "./client";

/** JSON request whose error message is the backend's `detail` — for bots,
 *  the gateway's own reason ("EURC_USD is already running (CUQuants:4)"). */
async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") message = body.detail;
      else if (Array.isArray(body?.detail)) {
        // FastAPI validation errors: "okx.tick_level: Input should be greater than 0"
        message = body.detail
          .map((d: { loc?: unknown[]; msg?: string }) =>
            `${(d.loc ?? []).filter((p) => p !== "body").join(".")}: ${d.msg ?? "invalid"}`)
          .join("; ");
      }
    } catch {
      /* non-JSON error body: keep the status message */
    }
    throw new ApiError(message, res.status);
  }
  return res.json() as Promise<T>;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return call<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const m = encodeURIComponent;

export const fetchBotStatus = () => call<BotStatus>("/bots");
export const startBot = (market: string) => post<unknown>(`/bots/${m(market)}/start`);
export const stopBot = (market: string) => post<unknown>(`/bots/${m(market)}/stop`);
export const readBotFile = (market: string, kind: BotFileKind) =>
  call<BotFile>(`/bots/${m(market)}/files/${kind}`);
export const saveBotFile = (market: string, kind: BotFileKind, content: string, base_sha256: string) =>
  post<BotFileSaved>(`/bots/${m(market)}/files/${kind}`, { content, base_sha256 });
export const launchMarket = (req: LaunchMarketRequest) =>
  post<LaunchMarketResult>("/bots/launch", req);
