from fastapi import APIRouter, HTTPException
from models.deck import DeckImportRequest, DeckImportResponse
from services.archidekt_client import fetch_deck

router = APIRouter(prefix="/api", tags=["import"])

@router.post("/import/archidekt", response_model=DeckImportResponse)
async def import_archidekt(req: DeckImportRequest):
    deck = await fetch_deck(req.archidekt_url)
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found or is private")
    return DeckImportResponse(**deck)
