from typing import Dict, List


DEFAULT_EXCHANGE_PAIRS: Dict[str, List[str]] = {
    "kraken": ["USDG/USD", "USDR/EUR", "USDD/EUR", "EURR/USD", "USDQ/EUR", "PYUSD/EUR", "EURR/USDT", "EURR/USDC"],
    "okx": ["PYUSD/USDT", "USDG/USDT", "USDC/USDT", "DAI/USDT", "PAXG/USDT"]
}


def get_exchange_pairs() -> Dict[str, List[str]]:
    """Return a defensive copy of configured exchange pairs."""
    return {exchange: pairs.copy() for exchange, pairs in DEFAULT_EXCHANGE_PAIRS.items()}
