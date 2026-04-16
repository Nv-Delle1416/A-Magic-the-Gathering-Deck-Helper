import asyncio
import re
from fastapi import APIRouter, HTTPException
from models.deck import RecommendRequest
from models.recommendation import RecommendResponse
from services.scryfall_client import search_cards, get_commander
from services.prompt_builder import JankPreferences, build_query_generation_prompt, build_selection_prompt
from services.ollama_client import generate_recommendations, extract_json_from_response

router = APIRouter(prefix="/api", tags=["recommend"])

# Fallback queries used if Pass 1 JSON parsing fails
_FALLBACK_QUERIES = [
    "o:draw t:instant",
    "o:sacrifice o:token",
    "t:artifact o:mana",
]


def _build_legality_suffix(color_identity: list[str]) -> str:
    """Build the server-side Scryfall legality constraints."""
    color_str = "".join(color_identity) if color_identity else "WUBRG"
    return f"f:commander id<={color_str}"


def _sanitize_query(query: str) -> str:
    """Strip any legality or format filters the LLM may have injected."""
    query = re.sub(r"f:\w+", "", query)
    query = re.sub(r"id<=\w+", "", query)
    return query.strip()


async def _execute_queries(
    queries: list[str],
    legality_suffix: str,
    limit_per_query: int = 20,
) -> list[dict]:
    """Execute queries in parallel, enforce legality, deduplicate by card name."""
    async def fetch(q: str) -> list[dict]:
        full_query = f"{_sanitize_query(q)} {legality_suffix}"
        return await search_cards(query=full_query, limit=limit_per_query)

    results = await asyncio.gather(*[fetch(q) for q in queries], return_exceptions=True)

    seen: set[str] = set()
    candidates: list[dict] = []
    for batch in results:
        if isinstance(batch, Exception):
            continue
        for card in batch:
            name = card.get("name", "")
            if name and name not in seen:
                seen.add(name)
                candidates.append(card)
    return candidates


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    # 1. Commander lookup and validation
    commander = await get_commander(req.commander_name)
    if commander is None:
        raise HTTPException(
            status_code=400,
            detail=f"Commander not found or not legal in Commander format: '{req.commander_name}'"
        )

    color_identity = commander.get("color_identity", [])
    legality_suffix = _build_legality_suffix(color_identity)

    # 2. Pass 1 — LLM generates deck analysis + Scryfall queries
    prefs = JankPreferences(
        synergy_first=req.synergy_first,
        hidden_gems=req.hidden_gems,
        chaos_injection=req.chaos_injection,
        llm_choice=req.llm_choice,
    )
    pass1_prompt = build_query_generation_prompt(
        concept=req.concept,
        commander=commander,
        existing_deck=[c.model_dump() for c in req.existing_deck] if req.existing_deck else None,
        preferences=prefs,
    )
    try:
        pass1_raw = await generate_recommendations(prompt=pass1_prompt, model=req.model)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    pass1_data = extract_json_from_response(pass1_raw)
    if pass1_data and isinstance(pass1_data.get("queries"), list) and pass1_data["queries"]:
        queries = [str(q) for q in pass1_data["queries"][:8]]
        deck_analysis = str(pass1_data.get("analysis", ""))
    else:
        # Fallback: use generic queries if JSON parsing failed
        queries = _FALLBACK_QUERIES
        deck_analysis = ""

    # 3. Execute queries in parallel with legality enforcement
    candidates = await _execute_queries(queries, legality_suffix)

    if len(candidates) < 10:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve sufficient card candidates from Scryfall"
        )

    # 4. Pass 2 — LLM selects and reasons about 10 cards from the candidate pool
    pass2_prompt = build_selection_prompt(
        concept=req.concept,
        commander=commander,
        deck_analysis=deck_analysis,
        candidates=candidates,
        preferences=prefs,
        existing_deck=[c.model_dump() for c in req.existing_deck] if req.existing_deck else None,
    )
    try:
        result = await generate_recommendations(prompt=pass2_prompt, model=req.model)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return RecommendResponse(
        recommendations_text=result,
        cards_used_as_context=[c["name"] for c in candidates],
    )
