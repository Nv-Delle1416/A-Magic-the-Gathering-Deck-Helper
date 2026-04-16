from fastapi import APIRouter, HTTPException
from models.deck import RecommendRequest
from models.recommendation import RecommendResponse
from services.scryfall_client import search_cards
from services.prompt_builder import JankPreferences, build_recommendation_prompt
from services.ollama_client import generate_recommendations

router = APIRouter(prefix="/api", tags=["recommend"])

@router.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    # color_identity removed from RecommendRequest; router will be rewritten in Task 5
    color_filter = ""
    base_query = "f:commander"

    # Try to enrich the query with a concept keyword, but fall back to
    # base query if the keyword yields no results (e.g. "Grixis" is not oracle text)
    MTG_KEYWORDS = {
        "flying", "trample", "lifelink", "deathtouch", "haste", "vigilance",
        "first", "reach", "flash", "hexproof", "indestructible", "menace",
        "sacrifice", "counter", "draw", "discard", "exile", "graveyard",
        "token", "copy", "proliferate", "infect", "equip", "enchant",
        "ramp", "bounce", "mill", "storm", "cascade", "flashback",
        "morph", "cycling", "kicker", "convoke", "emerge", "delve",
    }
    concept_words = req.concept.lower().split() if req.concept else []
    concept_keyword = next(
        (w for w in concept_words if w in MTG_KEYWORDS), ""
    )
    query = f"{base_query} o:{concept_keyword}" if concept_keyword else base_query
    cards = await search_cards(query=query, limit=30)

    # Fall back to base query without oracle filter if the enriched query returns nothing
    if not cards and concept_keyword:
        cards = await search_cards(query=base_query, limit=30)

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
