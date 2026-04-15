from fastapi import APIRouter, HTTPException
from models.deck import RecommendRequest
from models.recommendation import RecommendResponse
from services.scryfall_client import search_cards
from services.prompt_builder import JankPreferences, build_recommendation_prompt
from services.ollama_client import generate_recommendations

router = APIRouter(prefix="/api", tags=["recommend"])

@router.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    color_filter = "".join(req.color_identity) if req.color_identity else ""
    query = f"id<={color_filter}" if color_filter else "f:commander"
    # Add a keyword from the concept to narrow Scryfall results
    concept_keyword = req.concept.split()[0].lower() if req.concept else ""
    if concept_keyword:
        query += f" o:{concept_keyword}"

    cards = await search_cards(query=query, limit=30)
    if not cards:
        raise HTTPException(status_code=502, detail="Could not retrieve card data from Scryfall")

    prefs = JankPreferences(
        synergy_first=req.synergy_first,
        hidden_gems=req.hidden_gems,
        chaos_injection=req.chaos_injection,
        llm_choice=req.llm_choice,
    )
    prompt = build_recommendation_prompt(
        concept=req.concept,
        cards=cards,
        preferences=prefs,
        existing_deck=[c.model_dump() for c in req.existing_deck] if req.existing_deck else None,
    )
    try:
        result = await generate_recommendations(prompt=prompt, model=req.model)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return RecommendResponse(
        recommendations_text=result,
        cards_used_as_context=[c["name"] for c in cards],
    )
