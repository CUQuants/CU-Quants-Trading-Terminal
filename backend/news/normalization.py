"""Normalize provider records and match news without changing cached articles."""

import math
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser

from models import NewsArticle, NewsCategory


_CATEGORIES = {"Crypto", "Trad-Fi", "FX/Macro", "Geo-Politics"}
_CRYPTO_SOURCES = {"cryptopanic", "coindesk", "messari"}
_FX_SOURCES = {"marketaux"}
_GEO_PATTERN = re.compile(
    r"\b(?:wars?|wartime|conflicts?|sanctions?|sanctioned|military|geopolit\w*|"
    r"nato|ukraine|russia|taiwan|iran|missiles?|nuclear|coups?|invasions?|"
    r"ceasefires?|diplomacy|treaty|treaties|referendums?|terrorism|troops?|"
    r"airstrikes?|battalions?)\b",
    re.IGNORECASE,
)
_CRYPTO_PATTERN = re.compile(
    r"\b(?:bitcoin|btc|xbt|ethereum|eth|crypto\w*|blockchain|defi|nfts?|"
    r"altcoins?|solana|ripple|xrp|stablecoins?|web3|coinbase|binance|tokens?|"
    r"mining|doge|dogecoin|litecoin|polkadot)\b",
    re.IGNORECASE,
)
_FX_PATTERN = re.compile(
    r"\b(?:forex|currenc(?:y|ies)|exchange rates?|dollar index|eurusd|gbpusd|"
    r"usdjpy|dxy|gold prices?|crude oil|commodit(?:y|ies)|brent|wti|oil prices?|"
    r"fx markets?)\b",
    re.IGNORECASE,
)
_ASSET_ALIASES = {
    "BTC": ("XBT", "Bitcoin"),
    "ETH": ("Ethereum", "Ether"),
    "SOL": ("Solana",),
    "XRP": ("Ripple",),
    "DOGE": ("Dogecoin",),
    "LTC": ("Litecoin",),
    "ADA": ("Cardano",),
    "DOT": ("Polkadot",),
    "AVAX": ("Avalanche",),
    "LINK": ("Chainlink",),
    "BCH": ("Bitcoin Cash",),
    "BNB": ("Binance Coin",),
    "USDT": ("Tether",),
    "USDC": ("USD Coin",),
    "USD": ("US dollar", "U.S. dollar"),
    "EUR": ("Euro",),
    "GBP": ("British pound", "Pound sterling"),
    "JPY": ("Japanese yen",),
    "CHF": ("Swiss franc",),
    "AUD": ("Australian dollar",),
    "CAD": ("Canadian dollar",),
    "NZD": ("New Zealand dollar",),
    "XAU": ("Gold",),
    "XAG": ("Silver",),
}
_ALIAS_SYMBOLS = {
    alias.casefold(): symbol
    for symbol, aliases in _ASSET_ALIASES.items()
    for alias in (symbol, *aliases)
}
_AMBIGUOUS_SYMBOLS = {"ADA", "DOT", "LINK", "SOL"}
_BLOCK_TAGS = {
    "article", "blockquote", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul",
}


class _TextParser(HTMLParser):
    """Keep readable text, excluding comments and script/style contents."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif not self.hidden and tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parser = _TextParser()
    try:
        parser.feed(unescape(value))
        parser.close()
    except (AssertionError, ValueError):
        # Older supported Python versions reject malformed HTML declarations.
        return ""
    return " ".join("".join(parser.parts).split())


def _parse_timestamp(value: object) -> datetime | None:
    """Accept provider dates as UTC; never invent a date for invalid input."""
    if isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, (int, float)):
        try:
            timestamp = float(value)
            if not math.isfinite(timestamp):
                return None
            if abs(timestamp) >= 100_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str) and value.strip():
        value = value.strip()
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
            return _parse_timestamp(float(value))
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                result = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
    else:
        return None
    try:
        if result.tzinfo is None:
            return result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        return None


def _canonical_asset(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    alias = _ALIAS_SYMBOLS.get(value.casefold())
    if alias:
        return alias
    value = value.upper()
    if re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=]{0,19}", value):
        return value
    return None


def _canonical_pair(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parts = re.split(r"[/_-]", value.strip())
    if len(parts) != 2:
        return None
    base, quote = (_canonical_asset(part) for part in parts)
    return f"{base}/{quote}" if base and quote else None


def _has_term(text: str, term: str, *, case_sensitive: bool = False) -> bool:
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.search(
        rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text, flags
    ) is not None


def _mentions_asset(text: str, symbol: str) -> bool:
    if _has_term(text, symbol, case_sensitive=symbol in _AMBIGUOUS_SYMBOLS):
        return True
    for alias in _ASSET_ALIASES.get(symbol, ()):
        if alias == "Bitcoin":
            if re.search(r"\bBitcoin\b(?!\s+Cash\b)", text, re.IGNORECASE):
                return True
        elif _has_term(text, alias):
            return True
    return False


def _category(source: str, title: str, summary: str, explicit: object) -> NewsCategory:
    text = f"{title} {summary}"
    if _GEO_PATTERN.search(text):
        return "Geo-Politics"
    if isinstance(explicit, str) and explicit.strip() in _CATEGORIES:
        return explicit.strip()
    source_base = source.split("/", 1)[0].strip().casefold()
    if source_base in _CRYPTO_SOURCES:
        return "Crypto"
    if source_base in _FX_SOURCES:
        return "FX/Macro"
    if _CRYPTO_PATTERN.search(text):
        return "Crypto"
    if _FX_PATTERN.search(text):
        return "FX/Macro"
    return "Trad-Fi"


def normalize_article(raw: dict) -> NewsArticle | None:
    """Convert one provider record; malformed optional fields stay empty."""
    if not isinstance(raw, dict):
        return None
    title = _clean_text(raw.get("title"))
    if not title:
        return None
    source = _clean_text(raw.get("source")) or "Unknown"
    summary = _clean_text(raw.get("summary"))
    url = raw.get("url")
    timestamp = next(
        (raw[key] for key in ("published_at", "dt", "timestamp", "datetime")
         if raw.get(key) is not None),
        None,
    )
    assets: list[str] = []
    raw_assets = raw.get("assets", [])
    if isinstance(raw_assets, list):
        for value in raw_assets:
            symbol = _canonical_asset(value)
            if symbol and symbol not in assets:
                assets.append(symbol)
    text = f"{title} {summary}"
    for symbol in _ASSET_ALIASES:
        if symbol not in assets and _mentions_asset(text, symbol):
            assets.append(symbol)
    return NewsArticle(
        source=source,
        title=title,
        summary=summary,
        url=url.strip() if isinstance(url, str) else "",
        published_at=_parse_timestamp(timestamp),
        category=_category(source, title, summary, raw.get("category")),
        assets=assets,
    )


def match_article(
    article: NewsArticle, pairs: list[str], assets: list[str] | None = None
) -> NewsArticle:
    """Match requested pairs/assets on a copy, considering pair bases only."""
    text = f"{article.title} {article.summary}"
    mentioned = set(article.assets)
    hits: list[str] = []
    for value in pairs:
        pair = _canonical_pair(value)
        if not pair or pair in hits:
            continue
        base, quote = pair.split("/")
        base_terms = (base, "XBT") if base == "BTC" else (base,)
        quote_terms = (quote, "XBT") if quote == "BTC" else (quote,)
        explicit = any(
            _has_term(text, f"{base_term}{separator}{quote_term}")
            for base_term in base_terms
            for quote_term in quote_terms
            for separator in ("/", "-", "_")
        )
        if explicit or base in mentioned or _mentions_asset(text, base):
            hits.append(pair)
    for value in assets or []:
        symbol = _canonical_asset(value)
        if not symbol or symbol in hits:
            continue
        if symbol in mentioned or _mentions_asset(text, symbol):
            hits.append(symbol)
    result = article.model_copy(deep=True)
    result.matched = bool(hits)
    result.match_terms = hits
    return result


def deduplicate_articles(articles: Iterable[NewsArticle]) -> list[NewsArticle]:
    """Keep the first exact nonempty URL; retain URL variants and empty URLs."""
    seen: set[str] = set()
    result: list[NewsArticle] = []
    for article in articles:
        if article.url:
            if article.url in seen:
                continue
            seen.add(article.url)
        result.append(article)
    return result
