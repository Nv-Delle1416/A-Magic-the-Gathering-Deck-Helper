from fastapi import APIRouter, HTTPException
from services.scryfall_client import get_card_by_name

router = APIRouter(prefix="/api", tags=["cards"])

@router.get("/card/{name}")
async def card_lookup(name: str):
    card = await get_card_by_name(name)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card
