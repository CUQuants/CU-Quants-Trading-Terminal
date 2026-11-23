/**
 * speedbyte bot control — the gateway's `POST /v1/bots`, via the terminal
 * backend's `/bots` routes (backend/routes/bots.py).
 */
export interface BotMarket {
  market: string;
  /** A tmux session named after the market exists. */
  session: boolean;
  /** A `python3 src/main.py MARKET` process exists, wherever it runs. */
  running: boolean;
  /** Where it runs, e.g. "CUQuants:1". Comma-separated if more than one. */
  location: string;
  instances: number;
  /** Where Start types the start line ("CUQuants:4", or its own session);
   *  "" = Start makes a new CUQuants window. Missing on an older gateway. */
  home?: string;
  /** Last non-blank line of the bot's pane. */
  last: string;
}

export interface BotStatus {
  root: string;
  tmux_server: boolean;
  markets: BotMarket[];
  error?: string;
}

export type BotFileKind = "config" | "subaccount";

export interface BotFile {
  market: string;
  kind: BotFileKind;
  path: string;
  content: string;
  sha256: string;
}

export interface BotFileSaved {
  market: string;
  kind: BotFileKind;
  sha256: string;
  /** Always null from the terminal; a name means the gateway predates
   *  `backup: false` and kept a copy anyway. */
  backup: string | null;
}

export interface ExchangeLaunchSettings {
  enabled: boolean;
  trading_pair: string;
  reference_pair: string;
  minimum_spread: string;
  center_buffer: string;
  tick_level: string;
}

export interface LaunchMarketRequest {
  market: string;
  okx: ExchangeLaunchSettings;
  kraken: ExchangeLaunchSettings & { proxy_exchange: "kraken" | "kraken_prime" };
  gemini: ExchangeLaunchSettings;
}

export interface LaunchMarketResult {
  market: string;
  config: string;
  subaccount: string;
  /** e.g. "CUQuants:5". Missing on an older gateway (it made a session). */
  where?: string;
}
