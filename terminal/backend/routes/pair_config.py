


DEFAULT_EXCHANGE_PAIRS: dict[str, list[str]] = {
    "kraken": ["USDG/USD", "USDR/EUR", "USDD/EUR", "EURR/USD", "USDQ/EUR", "PYUSD/EUR", "EURR/USDT", "EURR/USDC"],
    "okx": ["PYUSD/USDT", "USDG/USDT", "USDC/USDT", "PAXG/USDT"]
}


def get_exchange_pairs() -> dict[str, list[str]]:
    """Return a defensive copy of configured exchange pairs."""
    return {exchange: pairs.copy() for exchange, pairs in DEFAULT_EXCHANGE_PAIRS.items()}
