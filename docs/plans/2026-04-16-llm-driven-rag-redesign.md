# Design: LLM-Driven RAG Redesign + Commander Legality

**Date:** 2026-04-16  
**Status:** Approved

---

## Problem

The current recommendation pipeline produces poor results because the LLM is handed a pre-filtered list of 30 cards from a shallow single Scryfall query and asked to pick 10. It has no agency over what cards are retrieved, so it ends up justifying whatever was already fetched rather than performing real analysis. The Scryfall query itself is too basic — one keyword extracted from the concept string.

Additionally, the `color_identity` field requires the user to manually specify colors, which is error-prone and unnecessary given that color identity is derivable from the commander.

---

## Solution: Two-Pass LLM Pipeline + Commander Lookup

### Architecture

```
Request (concept + commander_name + existing_deck + jank_prefs)
  │
  ├─ 1. Commander Lookup (Scryfall fuzzy)
  │       → validate legality
  │       → extract color_identity
  │
  ├─ 2. LLM Pass 1 — Analysis + Query Generation
  │       Input:  concept, commander card data, existing deck list
  │       Output: deck analysis + 5-8 Scryfall query strings
  │
  ├─ 3. Query Execution (parallel)
  │       Each query gets `f:commander id<=<colors>` appended server-side
  │       Results deduplicated by card name
  │       Target: ~80 candidate cards
  │
  └─ 4. LLM Pass 2 — Selection + Reasoning
          Input:  concept, commander data, deck analysis from Pass 1,
                  candidate card pool, jank preferences
          Output: 10 final recommendations with gap-filling reasoning
```

### Pass 1 Prompt

Instructs the LLM to:
1. Identify the deck's themes, mechanics, and win conditions based on the concept and commander
2. If an existing deck is provided: identify specific gaps (ramp, removal, card draw, synergy payoffs, etc.)
3. Output a structured JSON block containing:
   - `analysis`: a short paragraph summarizing themes and gaps
   - `queries`: array of 5-8 Scryfall query strings (oracle text / type searches), e.g. `o:"sacrifice" o:"token"`, `t:enchantment o:"draw"`, etc.

The LLM is told to write queries as Scryfall oracle/type search terms only — the server appends legality constraints.

### Pass 2 Prompt

Instructs the LLM to:
1. Review the deck analysis from Pass 1
2. Select 10 cards from the candidate pool that fill identified gaps or advance themes
3. For each card: name, which specific gap or theme it addresses, and the synergy or interaction that makes it interesting
4. Never justify a card purely by describing what it does — must reference a gap or interaction

### Legality Enforcement

All Scryfall queries have two constraints appended server-side (not by the LLM):
- `f:commander` — enforces Commander format legality, excludes banned cards
- `id<=<color_identity>` — enforces color identity derived from commander lookup

If a query returns zero results after filtering, it is dropped silently. If fewer than 3 queries return results, the endpoint returns a 502.

---

## Data Model Changes

### Backend

**`RecommendRequest` (`models/deck.py`)**
- Remove: `color_identity: list[str]`
- Add: `commander_name: str`

**New service: `commander_service.py`** (or extend `scryfall_client.py`)
- `get_commander(name: str) -> dict` — fuzzy lookup, validates the card is a legal commander (legendary creature or has "can be your commander" text), returns slimmed card data including `color_identity`

**`prompt_builder.py`**
- Add `build_query_generation_prompt(concept, commander, existing_deck) -> str` — Pass 1 prompt
- Add `build_selection_prompt(concept, commander, analysis, candidates, preferences) -> str` — Pass 2 prompt
- Remove `build_recommendation_prompt` (replaced by the two above)

**`ollama_client.py`**
- Add `extract_json_block(text: str) -> dict` helper — parses the JSON block from Pass 1 response
- `generate_recommendations` signature remains the same (used for Pass 2)

**`routers/recommend.py`**
- Replace single-query + single-LLM-call flow with the two-pass pipeline
- Commander lookup at request entry, 400 on invalid commander
- Parallel execution of Pass 1 queries using `asyncio.gather`

### Frontend

**`models` / `api/client.ts`**
- Replace `color_identity` with `commander_name: string` in `RecommendRequest`

**`pages/Home.tsx` / `components/DeckEditor.tsx`**
- Replace color identity checkboxes with a commander name text input
- Optionally display resolved commander card data (name, colors, art) after lookup confirmation

---

## Error Handling

| Scenario | Response |
|---|---|
| Commander not found on Scryfall | 400: "Commander not found: {name}" |
| Commander is not legal in Commander format | 400: "'{name}' is not a legal Commander" |
| Pass 1 LLM returns unparseable JSON | Fallback: use 3 generic oracle-text queries derived from concept keywords |
| Fewer than 3 queries return results | 502: "Could not retrieve sufficient card candidates" |
| Pass 2 LLM unavailable | 503 (existing behavior) |

---

## Out of Scope

- Multi-format support (Standard, Modern, etc.) — Commander only
- Parsing LLM output into structured card objects (separate future improvement)
- `/api/improve` endpoint for deck cuts
