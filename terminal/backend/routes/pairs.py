from fastapi import APIRouter

from .pair_config import get_exchange_pairs

router = APIRouter(prefix="/pairs", tags=["pairs"])


@router.get("", response_model=dict[str, list[str]])
async def get_pairs() -> dict[str, list[str]]:
    """Return configured default exchange/pair combinations."""
    return get_exchange_pairs()
