"""The files a new speedbyte market starts with — Bot Monitor's Launch Market.

Ported from xlrts (`bot_monitor_window._LaunchMarketDialog`), so a market
launched from the terminal gets byte-for-byte the same config layout as one
launched from xlrts. The one difference is that every value is validated here
first (`LaunchRequest`): xlrts pasted the raw text fields into the YAML, so a
stray quote could change its structure. The gateway checks the result again —
it must parse, and its `market:` must match — before writing anything.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

#: Same rule as the gateway's MARKET_RE: the name becomes a filename and a
#: tmux window name.
MARKET_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
#: A venue symbol (EURQ-USD, EURQ/USD, eurqusd) or blank. No quotes, so it is
#: safe inside a single-quoted YAML scalar.
PAIR_PATTERN = r"^([A-Za-z0-9][A-Za-z0-9/_.:-]{0,31})?$"


class ExchangeSettings(BaseModel):
    enabled: bool = False
    trading_pair: str = Field("", pattern=PAIR_PATTERN)
    reference_pair: str = Field("", pattern=PAIR_PATTERN)
    #: Decimals, not floats: written as typed ("2.00", "0.0001"), never as
    #: "1e-05", which YAML would read back as a string.
    minimum_spread: Decimal = Field(ge=0)
    center_buffer: Decimal
    tick_level: Decimal = Field(gt=0)


class KrakenSettings(ExchangeSettings):
    proxy_exchange: Literal["kraken", "kraken_prime"] = "kraken_prime"


class LaunchRequest(BaseModel):
    market: str = Field(pattern=MARKET_PATTERN)
    okx: ExchangeSettings
    kraken: KrakenSettings
    gemini: ExchangeSettings


def _num(value: Decimal) -> str:
    return format(value, "f")


def _quoted(value: str) -> str:
    return f"'{value}'"


def _bool(value: bool) -> str:
    return "true" if value else "false"


def config_yaml(req: LaunchRequest) -> str:
    market = req.market
    okx, krk, gem = req.okx, req.kraken, req.gemini
    return (
        f"market: '{market}'\n"
        f"subaccount: '{market}'\n"
        f"\n"
        f"##\n## Kraken Settings\n##\n"
        f"kraken:\n"
        f"  trading_pair: {_quoted(krk.trading_pair)}\n"
        f"  enabled: {_bool(krk.enabled)}\n"
        f"  ##\n  ## Pricing Settings\n  ##\n"
        f"  pricing_model: 'default'\n"
        f"  reference_pair: {_quoted(krk.reference_pair)}\n"
        f"  center_buffer: {_num(krk.center_buffer)} ## in bps\n"
        f"  minimum_spread: {_num(krk.minimum_spread)} ## in bps\n"
        f"  pricing_abstract: None\n"
        f"  ##\n  ## Sizing Settings\n  ##\n"
        f"  sizing_model: 'default'\n"
        f"  sizing_abstract: None\n"
        f"  ##\n  ## Market Settings\n  ##\n"
        f"  tick_level: {_num(krk.tick_level)}\n"
        f"  market_abstract: None\n"
        f"  ##\n  ## Access\n  ##\n"
        f"  ## No Kraken credentials: speedbyte reaches Kraken only through the\n"
        f"  ## CU Quants Proxy, using the CUQ_PROXY_* environment on the box.\n"
        f"  ## ws_url blank = derived from CUQ_PROXY_URL.\n"
        f"  ws_url: ''\n"
        f"  ## 'kraken' (spot key) or 'kraken_prime' (the Prime account).\n"
        f"  proxy_exchange: '{krk.proxy_exchange}'\n"
        f"  proxy_timeout: 15.0\n"
        f"  tier: 'starter'\n"
        f"\n"
        f"##\n## Gemini Settings\n##\n"
        f"gemini:\n"
        f"  trading_pair: {_quoted(gem.trading_pair)}\n"
        f"  enabled: {_bool(gem.enabled)}\n"
        f"  ##\n  ## Pricing Settings\n  ##\n"
        f"  pricing_model: 'default'\n"
        f"  reference_pair: {_quoted(gem.reference_pair)}\n"
        f"  center_buffer: {_num(gem.center_buffer)} ## in bps\n"
        f"  minimum_spread: {_num(gem.minimum_spread)} ## in bps\n"
        f"  pricing_abstract: None\n"
        f"  ##\n  ## Sizing Settings\n  ##\n"
        f"  sizing_model: 'default'\n"
        f"  sizing_abstract: None\n"
        f"  ##\n  ## Market Settings\n  ##\n"
        f"  tick_level: {_num(gem.tick_level)}\n"
        f"  market_abstract: None\n"
        f"  ##\n  ## API Credentials\n  ##\n"
        f"  api_key: 'gemini_api_1'\n"
        f"  api_secret: 'gemini_secret_1'\n"
        f"\n"
        f"##\n## OKX Settings\n##\n"
        f"okx:\n"
        f"  trading_pair: {_quoted(okx.trading_pair)}\n"
        f"  enabled: {_bool(okx.enabled)}\n"
        f"  ##\n  ## Pricing Settings\n  ##\n"
        f"  pricing_model: 'default'\n"
        f"  reference_pair: {_quoted(okx.reference_pair)}\n"
        f"  center_buffer: {_num(okx.center_buffer)} ## in bps\n"
        f"  minimum_spread: {_num(okx.minimum_spread)} ## in bps\n"
        f"  pricing_abstract: None\n"
        f"  ##\n  ## Sizing Settings\n  ##\n"
        f"  sizing_model: 'default'\n"
        f"  sizing_abstract: None\n"
        f"  ##\n  ## Market Settings\n  ##\n"
        f"  tick_level: {_num(okx.tick_level)}\n"
        f"  market_abstract: None\n"
        f"  ##\n  ## API Credentials\n  ##\n"
        f"  api_key: 'OKX_API_1'\n"
        f"  api_secret: 'OKX_SECRET_1'\n"
        f"  passphrase: 'OKX_PASSPHRASE_1'\n"
    )


def subaccount_json(market: str, now: datetime | None = None) -> str:
    parts = market.split("_")
    base = parts[0] if len(parts) >= 1 else "BASE"
    quote = parts[1] if len(parts) >= 2 else "QUOTE"
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    data = {
        "market": market,
        "created_at": stamp,
        "last_updated": stamp,
        "balances": {
            "okx": {base: 0.0, quote: 0.0},
            "kraken": {base: 0.0, quote: 0.0},
            "gemini": {base: 0.0, quote: 0.0},
        },
    }
    return json.dumps(data, indent=2)
