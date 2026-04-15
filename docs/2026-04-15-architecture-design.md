# MTG Deck Advisor — Architecture Design

**Date:** 2026-04-15

---

## Overview

A web application that leverages local open-source LLMs (via Ollama) to provide
Magic: The Gathering deck recommendations. Users can build a deck from scratch or
import an existing deck from Archidekt, then receive AI-powered card suggestions
grounded in real card data from the Scryfall API.

The application deliberately avoids defaulting to EDHREC popularity scores. Instead,
the user controls the recommendation style through a set of preference checkboxes
that steer the LLM toward different discovery strategies.

---

## Architecture

```
Browser (React + TypeScript)
        |
        | HTTP (REST)
        v
FastAPI Backend (Python)
   |           |           |
   v           v           v
Ollama      Scryfall    Archidekt
(local LLM)  API         API
```

### Components

| Component | Role |
|-----------|------|
| **React + TypeScript** | Frontend UI — deck editor, jank preference controls, recommendation display |
| **FastAPI (Python)** | Backend orchestrator — prompt construction, API coordination, Ollama calls |
| **Ollama** | Local LLM runtime (e.g. `llama3`, `mistral`) — no API keys or costs |
| **Scryfall API** | Ground-truth card data — oracle text, color identity, legality, type line |
| **Archidekt API** | Deck import — fetches a user's existing deck list by URL or deck ID |

---

## Core Flows

### Flow 1 — Build From Scratch

1. User describes a deck concept (e.g. "Simic ramp that wins through combat damage with weird creatures").
2. User selects jank preference checkboxes (see below).
3. Frontend POSTs request to `/api/recommend`.
4. Backend queries Scryfall for cards matching the color identity and theme keywords.
5. Backend builds a RAG-style prompt: card oracle text is injected as context.
6. Ollama returns a structured list of recommended cards with reasoning.
7. Frontend renders recommendations with card previews (Scryfall image URLs).

### Flow 2 — Import and Improve an Archidekt Deck

1. User pastes an Archidekt deck URL or ID.
2. Backend calls Archidekt API to retrieve the deck list.
3. Backend enriches each card in the deck via Scryfall (oracle text, synergy tags).
4. User selects jank preferences.
5. Backend builds prompt with the full deck context + Scryfall-enriched card data.
6. Ollama returns suggestions: cards to add, cards to cut, and reasoning.
7. Frontend renders a diff-style view of the suggested changes.

---

## Jank Preference System

Users control the recommendation style via checkboxes in the UI. These preferences
are injected into the system prompt to steer the LLM's reasoning:

| Checkbox | Behavior |
|----------|----------|
| **Synergy-first** | LLM identifies mechanical synergies from oracle text — combos, keyword chains, unusual triggered effects — ignoring card popularity entirely |
| **Hidden Gems** | Prioritize cards with low EDHREC inclusion rates that still have strong textual synergy with the deck |
| **Theme + Chaos Injection** | Deliberately surface off-meta, weird, or meme-worthy cards that still advance the stated theme |
| **LLM's Choice** | Give the model full autonomy to blend any of the above based on context |

Multiple checkboxes can be selected simultaneously.

---

## RAG Strategy

Rather than embedding a full vector store (overkill for this use case), the backend
uses **on-demand Scryfall retrieval**:

1. Extract keywords, mechanics, and color identity from the user's request or deck.
2. Query Scryfall's search API (e.g. `o:keyword c:UG`) to retrieve a targeted set of candidate cards.
3. Trim retrieved cards to fit within Ollama's context window (~4k–8k tokens depending on model).
4. Inject card names + oracle text as a numbered list into the LLM prompt.
5. The LLM reasons over the injected cards, not its parametric memory — reducing hallucination.

---

## API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/recommend` | Generate card recommendations from a description + preferences |
| `POST` | `/api/import/archidekt` | Fetch and parse an Archidekt deck by URL or ID |
| `POST` | `/api/improve` | Analyze an existing deck list and suggest improvements |
| `GET`  | `/api/card/{name}` | Proxy a Scryfall card lookup for the frontend |

---

## Project Structure (Planned)

```
mtg-deck-advisor/
  docs/                          # Design documents
  backend/
    main.py                      # FastAPI app entry point
    routers/
      recommend.py
      import_deck.py
      cards.py
    services/
      ollama_client.py           # Ollama API wrapper
      scryfall_client.py         # Scryfall API wrapper
      archidekt_client.py        # Archidekt API wrapper
      prompt_builder.py          # RAG prompt construction
    models/
      deck.py                    # Pydantic models
      recommendation.py
  frontend/
    src/
      components/
        DeckEditor.tsx
        RecommendationPanel.tsx
        JankPreferences.tsx
        CardPreview.tsx
      pages/
        Home.tsx
      api/
        client.ts                # Typed API calls to FastAPI
    package.json
    tsconfig.json
  README.md
```

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM runtime | Ollama | Local, free, no API keys, supports llama3/mistral |
| Card data | Scryfall API | Authoritative, free, comprehensive oracle text |
| Deck import | Archidekt API | Public API, widely used by the MTG community |
| Backend | FastAPI + Python | Best LLM ecosystem; async-friendly |
| Frontend | React + TypeScript | Component model fits deck editor UX well |
| RAG approach | On-demand Scryfall retrieval | Avoids vector DB complexity; Scryfall search is fast and precise |

---

## Out of Scope (v1)

- User authentication / saved decks
- Price optimization (budget constraints)
- Full vector store / semantic search across all 26k+ cards
- Direct deck export back to Archidekt
- Multiplayer / social features
