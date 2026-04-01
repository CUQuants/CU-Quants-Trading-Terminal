from typing import Dict, List

from fastapi import APIRouter

from .pair_config import get_exchange_pairs

router = APIRouter(prefix="/pairs", tags=["pairs"])


@router.get("", response_model=Dict[str, List[str]])
async def get_pairs() -> Dict[str, List[str]]:
    """Return configured default exchange/pair combinations."""
    return get_exchange_pairs()
