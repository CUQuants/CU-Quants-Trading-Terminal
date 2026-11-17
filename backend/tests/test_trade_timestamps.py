import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exchange_services.timestamps import seconds_to_milliseconds


@pytest.mark.parametrize("value,expected", [
    (1730385593.0, "1730385593000"),
    ("1730385593.123456", "1730385593123"),
    (0, "0"),
    (None, ""), ("", ""), ("invalid", ""),
    ("NaN", ""), ("Infinity", ""), (-1, ""), (True, ""),
])
def test_seconds_to_milliseconds(value, expected):
    assert seconds_to_milliseconds(value) == expected


@pytest.mark.asyncio
async def test_kraken_trade_response_uses_milliseconds():
    from exchange_services.kraken_service import KrakenService

    response = {"result": {"trades": {"trade-1": {
        "pair": "XXBTZUSD", "time": 1730385593.123456,
        "type": "buy", "price": "1", "vol": "1", "fee": "0",
    }}}}
    service = KrakenService(base_url="https://api.kraken.com", simulated=True)
    with patch.object(service, "_private_request", new_callable=AsyncMock, return_value=response):
        trades = await service.get_trades()
    assert trades[0].timestamp == "1730385593123"
    assert int(trades[0].timestamp) < int("1730385594000")
