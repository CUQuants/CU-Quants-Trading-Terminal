"""
Kraken REST API Client
Fetches tradable asset pairs from Kraken
"""

import httpx
from typing import Dict, List, Any

KRAKEN_REST_URL = "https://api.kraken.com/0/public"


async def get_tradable_pairs() -> Dict[str, Any]:
    """Fetch all tradable asset pairs from Kraken REST API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{KRAKEN_REST_URL}/AssetPairs")
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            raise Exception(f"Kraken API error: {data['error']}")

        return data.get("result", {})


def get_websocket_pairs(pairs_data: Dict[str, Any]) -> List[str]:
    """
    Extract WebSocket pair names from Kraken asset pairs response.
    Kraken uses different pair names for REST vs WebSocket APIs.
    """
    ws_pairs = []
    for pair_name, pair_info in pairs_data.items():
        # Use wsname if available, otherwise use the pair name
        ws_name = pair_info.get("wsname")
        if ws_name:
            ws_pairs.append(ws_name)
    return ws_pairs


async def get_ticker(pair: str) -> Dict[str, Any]:
    """Fetch current ticker data for a specific pair"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{KRAKEN_REST_URL}/Ticker",
            params={"pair": pair}
        )
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            raise Exception(f"Kraken API error: {data['error']}")

        return data.get("result", {})
