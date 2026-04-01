import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.pair_config import DEFAULT_EXCHANGE_PAIRS, get_exchange_pairs
from routes.pairs import get_pairs


def test_get_exchange_pairs_returns_expected_defaults():
    pairs = get_exchange_pairs()

    assert pairs == DEFAULT_EXCHANGE_PAIRS
    assert set(pairs.keys()) == {"kraken", "okx", "gemini"}
    assert "BTC/USD" in pairs["kraken"]


def test_get_exchange_pairs_returns_defensive_copy():
    pairs = get_exchange_pairs()
    pairs["kraken"].append("DOGE/USD")

    fresh_pairs = get_exchange_pairs()
    assert "DOGE/USD" not in fresh_pairs["kraken"]


@pytest.mark.asyncio
async def test_pairs_route_returns_default_config():
    payload = await get_pairs()

    assert payload == DEFAULT_EXCHANGE_PAIRS
