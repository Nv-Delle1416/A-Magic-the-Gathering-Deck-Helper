# LLM-Driven RAG Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the shallow single-query Scryfall + single LLM-call pipeline with a two-pass system where the LLM drives card retrieval via generated Scryfall queries, and a commander name replaces the manual color identity field.

**Architecture:** Pass 1 sends the deck concept + commander data to the LLM and asks it to output a deck analysis and 5–8 Scryfall query strings as JSON. Those queries are executed in parallel with Commander legality constraints appended server-side. Pass 2 sends the deduplicated candidate pool back to the LLM for final selection with gap-filling reasoning.

**Tech Stack:** FastAPI, Pydantic v2, httpx async, asyncio.gather, ollama, React 19, TypeScript 6, Vite, Tailwind CSS v4

---

## Task 1: Update Backend Data Models

**Files:**
- Modify: `backend/models/deck.py`

Replace `color_identity` with `commander_name` on `RecommendRequest`. Add a new `CommanderInfo` model to carry resolved commander data through the pipeline.

**Step 1: Edit `RecommendRequest` in `backend/models/deck.py`**

Replace the current content with:

```python
from pydantic import BaseModel


class Card(BaseModel):
    name: str
    quantity: int = 1
    category: str = "Mainboard"


class DeckImportRequest(BaseModel):
    archidekt_url: str


class DeckImportResponse(BaseModel):
    name: str
    format: str
    cards: list[Card]


class CommanderInfo(BaseModel):
    name: str
    mana_cost: str
    type_line: str
    oracle_text: str
    color_identity: list[str]
    image_uri: str | None = None


class RecommendRequest(BaseModel):
    concept: str
    commander_name: str
    existing_deck: list[Card] = []
    synergy_first: bool = False
    hidden_gems: bool = False
    chaos_injection: bool = False
    llm_choice: bool = False
    model: str = "llama3"
```

**Step 2: Verify the file looks correct**

Read `backend/models/deck.py` to confirm changes.

**Step 3: Commit**

```bash
git add backend/models/deck.py
git commit -m "feat: replace color_identity with commander_name on RecommendRequest"
```

---

## Task 2: Add Commander Lookup to Scryfall Client

**Files:**
- Modify: `backend/services/scryfall_client.py`

Add a `get_commander` function that does a fuzzy card lookup, validates the result is a legal Commander (legendary creature, or has "can be your commander" in oracle text), and returns a `CommanderInfo`-shaped dict.

**Step 1: Write the failing test**

Create `backend/tests/test_commander_lookup.py`:

```python
import pytest
from services.scryfall_client import get_commander


@pytest.mark.asyncio
async def test_get_commander_valid():
    result = await get_commander("Atraxa, Praetors' Voice")
    assert result is not None
    assert result["name"] == "Atraxa, Praetors' Voice"
    assert "W" in result["color_identity"]
    assert "B" in result["color_identity"]
    assert "G" in result["color_identity"]
    assert "U" in result["color_identity"]


@pytest.mark.asyncio
async def test_get_commander_nonexistent():
    result = await get_commander("zzzznotacard12345")
    assert result is None


@pytest.mark.asyncio
async def test_get_commander_non_legendary_creature_returns_none():
    # Lightning Bolt is not a legal commander
    result = await get_commander("Lightning Bolt")
    assert result is None
```

**Step 2: Run to confirm they fail**

```
cd backend && pytest tests/test_commander_lookup.py -v
```

Expected: `AttributeError` or `ImportError` — `get_commander` does not exist yet.

**Step 3: Implement `get_commander` in `backend/services/scryfall_client.py`**

Add after the existing `get_card_by_name` function:

```python
async def get_commander(name: str) -> dict | None:
    """Fuzzy-lookup a card by name and validate it is a legal Commander.

    A card is a legal commander if:
    - Its type line contains 'Legendary Creature', OR
    - Its oracle text contains 'can be your commander'
    Returns None if the card is not found or is not a legal commander.
    """
    card = await get_card_by_name(name)
    if card is None:
        return None

    type_line = card.get("type_line", "")
    oracle_text = card.get("oracle_text", "")

    is_legendary_creature = "Legendary" in type_line and "Creature" in type_line
    can_be_commander = "can be your commander" in oracle_text.lower()

    if not (is_legendary_creature or can_be_commander):
        return None

    return card
```

**Step 4: Run tests to confirm they pass**

```
cd backend && pytest tests/test_commander_lookup.py -v
```

Expected: all 3 PASS (note: these hit the live Scryfall API).

**Step 5: Commit**

```bash
git add backend/services/scryfall_client.py backend/tests/test_commander_lookup.py
git commit -m "feat: add get_commander to scryfall_client with legality validation"
```

---

## Task 3: Rewrite prompt_builder.py for Two-Pass Pipeline

**Files:**
- Modify: `backend/services/prompt_builder.py`
- Modify: `backend/tests/test_prompt_builder.py`

Replace the single `build_recommendation_prompt` with two new functions: `build_query_generation_prompt` (Pass 1) and `build_selection_prompt` (Pass 2). Keep `JankPreferences` and `_pref_instructions` as-is.

**Step 1: Write failing tests**

Replace `backend/tests/test_prompt_builder.py` with:

```python
from services.prompt_builder import (
    JankPreferences,
    build_query_generation_prompt,
    build_selection_prompt,
)


# --- Pass 1: query generation prompt ---

def test_query_generation_includes_concept():
    commander = {
        "name": "Atraxa, Praetors' Voice",
        "type_line": "Legendary Creature — Phyrexian Angel Horror",
        "oracle_text": "Flying, vigilance, deathtouch, lifelink. At the beginning of your end step, proliferate.",
        "color_identity": ["W", "U", "B", "G"],
        "mana_cost": "{G}{W}{U}{B}",
    }
    prompt = build_query_generation_prompt(
        concept="Atraxa proliferate counters", commander=commander
    )
    assert "Atraxa" in prompt
    assert "proliferate counters" in prompt


def test_query_generation_includes_existing_deck():
    commander = {
        "name": "Atraxa, Praetors' Voice",
        "type_line": "Legendary Creature",
        "oracle_text": "proliferate",
        "color_identity": ["W", "U", "B", "G"],
        "mana_cost": "{G}{W}{U}{B}",
    }
    existing = [{"name": "Sol Ring", "quantity": 1}, {"name": "Sword of Truth and Justice", "quantity": 1}]
    prompt = build_query_generation_prompt(
        concept="Counters", commander=commander, existing_deck=existing
    )
    assert "Sol Ring" in prompt
    assert "Sword of Truth and Justice" in prompt


def test_query_generation_requests_json_output():
    commander = {
        "name": "Test Commander",
        "type_line": "Legendary Creature",
        "oracle_text": "",
        "color_identity": ["R"],
        "mana_cost": "{R}",
    }
    prompt = build_query_generation_prompt(concept="Test", commander=commander)
    assert "json" in prompt.lower()
    assert "queries" in prompt.lower()
    assert "analysis" in prompt.lower()


# --- Pass 2: selection prompt ---

def test_selection_prompt_includes_candidates():
    commander = {
        "name": "Atraxa, Praetors' Voice",
        "type_line": "Legendary Creature",
        "oracle_text": "proliferate",
        "color_identity": ["W", "U", "B", "G"],
        "mana_cost": "{G}{W}{U}{B}",
    }
    candidates = [
        {"name": "Contagion Engine", "mana_cost": "{6}", "type_line": "Artifact",
         "oracle_text": "When Contagion Engine enters, proliferate. At the beginning of your end step, proliferate."},
    ]
    prefs = JankPreferences(synergy_first=True)
    prompt = build_selection_prompt(
        concept="Proliferate counters",
        commander=commander,
        deck_analysis="Deck needs more proliferate enablers.",
        candidates=candidates,
        preferences=prefs,
    )
    assert "Contagion Engine" in prompt
    assert "Proliferate counters" in prompt
    assert "10" in prompt  # ask for 10 recommendations


def test_selection_prompt_includes_deck_analysis():
    commander = {
        "name": "Test",
        "type_line": "Legendary Creature",
        "oracle_text": "",
        "color_identity": ["R"],
        "mana_cost": "{R}",
    }
    prefs = JankPreferences()
    prompt = build_selection_prompt(
        concept="Test",
        commander=commander,
        deck_analysis="Missing ramp and draw.",
        candidates=[],
        preferences=prefs,
    )
    assert "Missing ramp and draw." in prompt


def test_selection_prompt_synergy_first_preference():
    commander = {
        "name": "Test",
        "type_line": "Legendary Creature",
        "oracle_text": "",
        "color_identity": ["R"],
        "mana_cost": "{R}",
    }
    prefs = JankPreferences(synergy_first=True)
    prompt = build_selection_prompt(
        concept="Test", commander=commander, deck_analysis="",
        candidates=[], preferences=prefs
    )
    assert "synergy" in prompt.lower()
```

**Step 2: Run to confirm they fail**

```
cd backend && pytest tests/test_prompt_builder.py -v
```

Expected: `ImportError` — `build_query_generation_prompt` and `build_selection_prompt` do not exist.

**Step 3: Rewrite `backend/services/prompt_builder.py`**

```python
from pydantic import BaseModel


class JankPreferences(BaseModel):
    synergy_first: bool = False
    hidden_gems: bool = False
    chaos_injection: bool = False
    llm_choice: bool = False


def _pref_instructions(prefs: JankPreferences) -> str:
    parts = []
    if prefs.synergy_first:
        parts.append(
            "- SYNERGY-FIRST: Focus exclusively on mechanical synergies found in oracle text. "
            "Ignore card popularity entirely. Identify keyword interactions, unusual triggers, "
            "and combo potential."
        )
    if prefs.hidden_gems:
        parts.append(
            "- HIDDEN GEMS: Prioritize cards that are underplayed and rarely seen in decklists. "
            "Surface cards that most players overlook but that have strong synergy with the deck concept."
        )
    if prefs.chaos_injection:
        parts.append(
            "- CHAOS INJECTION: Deliberately include some off-meta, jank, or meme-worthy cards "
            "that are surprising but still advance the theme. Embrace the weird."
        )
    if prefs.llm_choice or not parts:
        parts.append(
            "- Use your own judgment to blend synergy discovery, hidden gems, and creative chaos "
            "based on what would make this deck the most interesting to play."
        )
    return "\n".join(parts)


def build_query_generation_prompt(
    concept: str,
    commander: dict,
    existing_deck: list[dict] | None = None,
) -> str:
    """Pass 1 prompt: ask the LLM to analyze the deck and generate Scryfall queries."""
    deck_block = ""
    if existing_deck:
        deck_block = "\n\nCURRENT DECK:\n" + "\n".join(
            f"- {c['quantity']}x {c['name']}" for c in existing_deck
        )

    return f"""You are an expert Magic: The Gathering deck builder and Scryfall power user.

COMMANDER: {commander['name']}
Type: {commander['type_line']}
Oracle Text: {commander['oracle_text']}
Color Identity: {', '.join(commander['color_identity'])}
{deck_block}

DECK CONCEPT: {concept}

Your task:
1. Analyze the deck concept and commander to identify: key themes, mechanics, and win conditions.
2. If a current deck is provided, identify specific gaps: missing ramp, card draw, removal, synergy payoffs, or anything that weakens the strategy.
3. Generate 5 to 8 Scryfall search query strings that would surface cards filling those gaps or advancing those themes. Write only the oracle/type search portion — do NOT include color identity or format filters (those are added automatically).

Example queries:
- o:"proliferate" t:artifact
- o:"counter" o:"draw a card"
- t:enchantment o:"whenever a creature"
- o:"sacrifice" o:"token"

Respond ONLY with a JSON object in this exact format (no markdown, no explanation outside the JSON):
{{
  "analysis": "A short paragraph summarizing the deck themes and gaps identified.",
  "queries": [
    "query string 1",
    "query string 2",
    "..."
  ]
}}"""


def build_selection_prompt(
    concept: str,
    commander: dict,
    deck_analysis: str,
    candidates: list[dict],
    preferences: JankPreferences,
    existing_deck: list[dict] | None = None,
) -> str:
    """Pass 2 prompt: ask the LLM to select 10 cards from the candidate pool."""
    card_block = "\n".join(
        f"{i+1}. {c.get('name', 'Unknown')} | {c.get('mana_cost', '')} | {c.get('type_line', '')}\n"
        f"   {c.get('oracle_text', '').replace(chr(10), ' ')}"
        for i, c in enumerate(candidates)
    ) or "No card context provided."

    deck_block = ""
    if existing_deck:
        deck_block = "\n\nCURRENT DECK:\n" + "\n".join(
            f"- {c['quantity']}x {c['name']}" for c in existing_deck
        )

    pref_block = _pref_instructions(preferences)

    return f"""You are an expert Magic: The Gathering deck builder who loves finding creative, unusual synergies.

COMMANDER: {commander['name']} — {commander['oracle_text']}
DECK CONCEPT: {concept}
{deck_block}

DECK ANALYSIS (your prior assessment of themes and gaps):
{deck_analysis}

RECOMMENDATION STYLE (follow these instructions strictly):
{pref_block}

AVAILABLE CARDS (all are legal in Commander for this color identity — do not recommend cards outside this list):
{card_block}

Select exactly 10 cards from the list above that best address the identified gaps and advance the deck's themes.
For each card provide:
1. Card name (must be from the list above)
2. Which specific gap or theme this card addresses
3. The synergy or interaction that makes it interesting for this deck

Do NOT justify a card by describing what it does in isolation. Every recommendation must reference a specific gap or interaction with the commander or deck strategy.
Do NOT recommend cards based on how popular they are. Do NOT list staples without synergy reasoning.
Format your response as a numbered list."""
```

**Step 4: Run tests to confirm they pass**

```
cd backend && pytest tests/test_prompt_builder.py -v
```

Expected: all tests PASS.

**Step 5: Commit**

```bash
git add backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat: rewrite prompt_builder with two-pass LLM pipeline prompts"
```

---

## Task 4: Update ollama_client.py — Add JSON Extraction Helper

**Files:**
- Modify: `backend/services/ollama_client.py`

Add a `extract_json_from_response` helper that parses the JSON block from Pass 1's LLM output. The LLM may wrap JSON in a markdown code block — handle that case.

**Step 1: Write the failing test**

Create `backend/tests/test_ollama_client.py`:

```python
from services.ollama_client import extract_json_from_response


def test_extract_plain_json():
    text = '{"analysis": "Good deck.", "queries": ["o:proliferate"]}'
    result = extract_json_from_response(text)
    assert result["analysis"] == "Good deck."
    assert result["queries"] == ["o:proliferate"]


def test_extract_json_from_markdown_code_block():
    text = '```json\n{"analysis": "Needs ramp.", "queries": ["t:artifact o:mana"]}\n```'
    result = extract_json_from_response(text)
    assert result["analysis"] == "Needs ramp."


def test_extract_json_with_surrounding_text():
    text = 'Here is the analysis:\n{"analysis": "Synergy deck.", "queries": ["o:counter"]}\nDone.'
    result = extract_json_from_response(text)
    assert result["analysis"] == "Synergy deck."


def test_extract_json_returns_none_on_failure():
    result = extract_json_from_response("This is not JSON at all.")
    assert result is None
```

**Step 2: Run to confirm they fail**

```
cd backend && pytest tests/test_ollama_client.py -v
```

Expected: `ImportError` — `extract_json_from_response` does not exist.

**Step 3: Add `extract_json_from_response` to `backend/services/ollama_client.py`**

Add after the existing imports at the top:

```python
import json
import re
```

Add this function after `generate_recommendations`:

```python
def extract_json_from_response(text: str) -> dict | None:
    """Extract and parse a JSON object from LLM output.

    Handles plain JSON, JSON wrapped in markdown code blocks,
    and JSON embedded in surrounding prose.
    """
    # Strip markdown code block if present
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)

    # Find the first {...} block in the text
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        return None

    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return None
```

**Step 4: Run tests to confirm they pass**

```
cd backend && pytest tests/test_ollama_client.py -v
```

Expected: all 4 PASS.

**Step 5: Commit**

```bash
git add backend/services/ollama_client.py backend/tests/test_ollama_client.py
git commit -m "feat: add extract_json_from_response helper to ollama_client"
```

---

## Task 5: Rewrite the Recommend Router

**Files:**
- Modify: `backend/routers/recommend.py`

Replace the single-query + single-LLM-call flow with the full two-pass pipeline: commander lookup → Pass 1 LLM → parallel Scryfall queries with legality enforcement → deduplicate → Pass 2 LLM.

**Step 1: Rewrite `backend/routers/recommend.py`**

```python
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
    # Remove f:format and id<=X patterns the LLM might add
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
    pass1_prompt = build_query_generation_prompt(
        concept=req.concept,
        commander=commander,
        existing_deck=[c.model_dump() for c in req.existing_deck] if req.existing_deck else None,
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
    prefs = JankPreferences(
        synergy_first=req.synergy_first,
        hidden_gems=req.hidden_gems,
        chaos_injection=req.chaos_injection,
        llm_choice=req.llm_choice,
    )
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
```

**Step 2: Run existing tests to ensure nothing is broken**

```
cd backend && pytest -v
```

Expected: all existing tests pass. The router itself is not unit tested here (it requires a running Ollama instance).

**Step 3: Commit**

```bash
git add backend/routers/recommend.py
git commit -m "feat: rewrite recommend router with two-pass LLM-driven RAG pipeline"
```

---

## Task 6: Update Frontend API Client

**Files:**
- Modify: `frontend/src/api/client.ts`

Replace `color_identity` with `commander_name` on `RecommendRequest`. Remove the manual preference-flattening and align the sent payload with the backend model directly.

**Step 1: Edit `frontend/src/api/client.ts`**

Replace the `RecommendRequest` interface and `getRecommendations` function:

```typescript
export interface RecommendRequest {
  concept: string;
  commander_name: string;
  existing_deck: { name: string; quantity: number }[];
  model: string;
  synergy_first: boolean;
  hidden_gems: boolean;
  chaos_injection: boolean;
  llm_choice: boolean;
}
```

And update `getRecommendations`:

```typescript
export async function getRecommendations(
  req: RecommendRequest
): Promise<RecommendResponse> {
  const res = await fetch(`${BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Recommendation failed: ${res.statusText}`);
  return res.json();
}
```

Also remove the `JankPreferences` export interface from `client.ts` — it is no longer needed here since the fields are flat on `RecommendRequest`.

**Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: update API client to use commander_name and flat jank preference fields"
```

---

## Task 7: Update Frontend Home Page

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

Replace the color identity checkbox section with a commander name text input. Update state and the `handleRecommend` call to match the new `RecommendRequest` shape.

**Step 1: Edit `frontend/src/pages/Home.tsx`**

Key changes:
- Remove `MTG_COLORS`, `COLOR_LABELS`, `colorIdentity` state, `toggleColor`
- Add `commanderName` state (`useState("")`)
- Replace the color identity `<div>` block with a commander name `<input>`
- Update `handleRecommend` to pass `commander_name` and flat jank fields

Updated state section (replace lines 8–31):

```tsx
const [cards, setCards] = useState<DeckCard[]>([]);
const [concept, setConcept] = useState("");
const [commanderName, setCommanderName] = useState("");
const [prefs, setPrefs] = useState<JankPrefs>({
  synergy_first: false,
  hidden_gems: false,
  chaos_injection: false,
  llm_choice: true,
});
const [model, setModel] = useState("llama3");
const [loading, setLoading] = useState(false);
const [result, setResult] = useState<{ text: string; context: string[] } | null>(null);
const [error, setError] = useState<string | null>(null);
```

Updated `handleRecommend`:

```tsx
const handleRecommend = async () => {
  if (!concept.trim() || !commanderName.trim()) return;
  setLoading(true);
  setError(null);
  try {
    const res = await getRecommendations({
      concept,
      commander_name: commanderName,
      existing_deck: cards,
      model,
      synergy_first: prefs.synergy_first,
      hidden_gems: prefs.hidden_gems,
      chaos_injection: prefs.chaos_injection,
      llm_choice: prefs.llm_choice,
    });
    setResult({ text: res.recommendations_text, context: res.cards_used_as_context });
  } catch (e: unknown) {
    setError(e instanceof Error ? e.message : "Something went wrong");
  } finally {
    setLoading(false);
  }
};
```

Replace the color identity `<div>` block (lines 79–96) with:

```tsx
<div>
  <label className="block font-semibold text-sm mb-1">Commander Name</label>
  <input
    type="text"
    placeholder="e.g. Atraxa, Praetors' Voice"
    value={commanderName}
    onChange={(e) => setCommanderName(e.target.value)}
    className="w-full border rounded px-3 py-2 text-sm"
  />
</div>
```

Update the disabled condition on the Recommend button:

```tsx
disabled={loading || !concept.trim() || !commanderName.trim()}
```

Update the import line to remove unused `JankPreferences as JankPrefs` type if it was exported from the old interface — instead import from components:

```tsx
import type { DeckCard } from "../api/client";
import type { JankPreferences as JankPrefs } from "../components/JankPreferences";
```

> **Note:** If `JankPreferences` type is not exported from `JankPreferences.tsx`, define it inline or keep it local. Check `components/JankPreferences.tsx` to confirm its exports.

**Step 2: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat: replace color identity UI with commander name input"
```

---

## Task 8: Verify JankPreferences Component Type Export

**Files:**
- Read: `frontend/src/components/JankPreferences.tsx`

Check whether `JankPreferences` type is exported. If not, add the export so `Home.tsx` can import it cleanly. If the type is already defined and exported there, no change needed.

If `JankPreferences.tsx` does not export the type, add:

```tsx
export interface JankPreferences {
  synergy_first: boolean;
  hidden_gems: boolean;
  chaos_injection: boolean;
  llm_choice: boolean;
}
```

**Commit if changed:**

```bash
git add frontend/src/components/JankPreferences.tsx
git commit -m "fix: export JankPreferences type from component"
```

---

## Task 9: End-to-End Smoke Test

**Step 1: Start the backend**

```bash
cd backend && uvicorn main:app --reload
```

**Step 2: Start the frontend**

```bash
cd frontend && npm run dev
```

**Step 3: Open http://localhost:5173 and test**

1. Enter commander: `Atraxa, Praetors' Voice`
2. Enter concept: `Proliferate counters — win through infect and planeswalker ultimates`
3. Leave existing deck empty
4. Click "Get Recommendations"
5. Verify: recommendations reference specific gaps and synergies, not just card descriptions

**Step 4: Test invalid commander**

1. Enter commander: `zzznotacard`
2. Click "Get Recommendations"
3. Verify: error message appears (400 from backend)

**Step 5: Run full backend test suite**

```bash
cd backend && pytest -v
```

Expected: all tests pass.

---

## Task 10: Final Commit + Cleanup

**Step 1: Verify no dead code remains**

- `color_identity` field should be gone from `models/deck.py`, `api/client.ts`, and `Home.tsx`
- `build_recommendation_prompt` is removed from `prompt_builder.py`
- `CardRecommendation` model in `models/recommendation.py` can be removed (it was already dead code)

**Step 2: Remove `CardRecommendation` from `backend/models/recommendation.py`**

```python
from pydantic import BaseModel


class RecommendResponse(BaseModel):
    recommendations_text: str
    cards_used_as_context: list[str]
```

**Step 3: Commit**

```bash
git add backend/models/recommendation.py
git commit -m "chore: remove dead CardRecommendation model"
```
