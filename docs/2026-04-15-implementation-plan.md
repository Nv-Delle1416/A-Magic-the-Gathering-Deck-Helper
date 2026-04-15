# MTG Deck Advisor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a React + FastAPI web application that uses a local Ollama LLM with on-demand Scryfall card data retrieval to generate jank-friendly Magic: The Gathering deck recommendations, with support for importing existing Archidekt decks.

**Architecture:** FastAPI backend orchestrates calls to Ollama (local LLM), Scryfall API (card data), and Archidekt API (deck import). The LLM receives oracle text for relevant cards as RAG context. User-controlled jank preference checkboxes steer the prompt strategy.

**Tech Stack:** Python 3.11+, FastAPI, httpx, Pydantic v2, Ollama Python client, React 18, TypeScript, Vite, Tailwind CSS

---

## Task 1: Project Scaffolding

**Files:**
- Create: `backend/` (directory)
- Create: `frontend/` (directory)
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Initialize the git repo**

```bash
cd C:\Users\ndelle432@cable.comcast.com\Documents\mtg-deck-advisor
git init
```

Expected: `Initialized empty Git repository`

**Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
*.env
node_modules/
dist/
.DS_Store
```

**Step 3: Create backend/requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
httpx==0.27.0
pydantic==2.7.1
ollama==0.2.1
python-dotenv==1.0.1
```

**Step 4: Create backend/main.py skeleton**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MTG Deck Advisor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 5: Create the Python virtual environment and install deps**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Expected: All packages install without error.

**Step 6: Verify FastAPI starts**

```bash
uvicorn main:app --reload
```

Expected: `Uvicorn running on http://127.0.0.1:8000`

**Step 7: Commit**

```bash
git add .
git commit -m "feat: scaffold FastAPI backend"
```

---

## Task 2: Scryfall Client

**Files:**
- Create: `backend/services/scryfall_client.py`
- Create: `backend/tests/test_scryfall_client.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_scryfall_client.py
import pytest
from services.scryfall_client import search_cards, get_card_by_name

@pytest.mark.asyncio
async def test_search_cards_returns_list():
    results = await search_cards(query="o:flying c:W", limit=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    assert "name" in results[0]
    assert "oracle_text" in results[0]

@pytest.mark.asyncio
async def test_get_card_by_name_found():
    card = await get_card_by_name("Sol Ring")
    assert card is not None
    assert card["name"] == "Sol Ring"

@pytest.mark.asyncio
async def test_get_card_by_name_not_found():
    card = await get_card_by_name("ZZZNOTAREALCARD999")
    assert card is None
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_scryfall_client.py -v
```

Expected: ImportError — `scryfall_client` not found.

**Step 3: Create the Scryfall client**

```python
# backend/services/scryfall_client.py
import httpx
from typing import Optional

SCRYFALL_BASE = "https://api.scryfall.com"

def _slim_card(card: dict) -> dict:
    """Extract only the fields we need to keep prompt context small."""
    return {
        "name": card.get("name", ""),
        "mana_cost": card.get("mana_cost", ""),
        "type_line": card.get("type_line", ""),
        "oracle_text": card.get("oracle_text", card.get("card_faces", [{}])[0].get("oracle_text", "")),
        "color_identity": card.get("color_identity", []),
        "edhrec_rank": card.get("edhrec_rank"),
        "image_uri": card.get("image_uris", {}).get("normal"),
    }

async def search_cards(query: str, limit: int = 20) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SCRYFALL_BASE}/cards/search",
            params={"q": query, "order": "edhrec", "dir": "asc"},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        cards = data.get("data", [])[:limit]
        return [_slim_card(c) for c in cards]

async def get_card_by_name(name: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SCRYFALL_BASE}/cards/named",
            params={"fuzzy": name},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return _slim_card(resp.json())
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scryfall_client.py -v
```

Expected: All 3 tests PASS (requires internet access to Scryfall).

**Step 5: Commit**

```bash
git add backend/services/scryfall_client.py backend/tests/test_scryfall_client.py
git commit -m "feat: add Scryfall API client with card search and lookup"
```

---

## Task 3: Archidekt Client

**Files:**
- Create: `backend/services/archidekt_client.py`
- Create: `backend/tests/test_archidekt_client.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_archidekt_client.py
import pytest
from services.archidekt_client import fetch_deck

@pytest.mark.asyncio
async def test_fetch_deck_returns_card_list():
    # Use a known public Archidekt deck ID
    result = await fetch_deck("123456")
    assert result is not None
    assert "name" in result
    assert "cards" in result
    assert isinstance(result["cards"], list)
    assert len(result["cards"]) > 0
    assert "name" in result["cards"][0]

@pytest.mark.asyncio
async def test_fetch_deck_invalid_id_returns_none():
    result = await fetch_deck("000000000000invalid")
    assert result is None

def test_extract_deck_id_from_url():
    from services.archidekt_client import extract_deck_id
    url = "https://archidekt.com/decks/12345/my-deck"
    assert extract_deck_id(url) == "12345"

def test_extract_deck_id_from_plain_id():
    from services.archidekt_client import extract_deck_id
    assert extract_deck_id("12345") == "12345"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_archidekt_client.py -v
```

Expected: ImportError.

**Step 3: Create the Archidekt client**

```python
# backend/services/archidekt_client.py
import re
import httpx
from typing import Optional

ARCHIDEKT_BASE = "https://archidekt.com/api"

def extract_deck_id(url_or_id: str) -> str:
    """Extract numeric deck ID from a full Archidekt URL or a plain ID string."""
    match = re.search(r"/decks/(\d+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()

async def fetch_deck(url_or_id: str) -> Optional[dict]:
    deck_id = extract_deck_id(url_or_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ARCHIDEKT_BASE}/decks/{deck_id}/",
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        cards = [
            {
                "name": card["card"]["oracleCard"]["name"],
                "quantity": card["quantity"],
                "category": card.get("categories", ["Mainboard"])[0],
            }
            for card in data.get("cards", [])
        ]
        return {
            "name": data.get("name", "Imported Deck"),
            "format": data.get("deckFormat", "Unknown"),
            "cards": cards,
        }
```

**Step 4: Run tests**

```bash
pytest tests/test_archidekt_client.py -v
```

Expected: URL extraction tests pass. The live fetch tests pass if the deck ID is valid and public (update the test ID to a real public deck).

**Step 5: Commit**

```bash
git add backend/services/archidekt_client.py backend/tests/test_archidekt_client.py
git commit -m "feat: add Archidekt deck import client"
```

---

## Task 4: Ollama Client & Prompt Builder

**Files:**
- Create: `backend/services/ollama_client.py`
- Create: `backend/services/prompt_builder.py`
- Create: `backend/tests/test_prompt_builder.py`

**Step 1: Write failing tests for prompt builder**

```python
# backend/tests/test_prompt_builder.py
from services.prompt_builder import build_recommendation_prompt, JankPreferences

def test_prompt_includes_card_context():
    cards = [{"name": "Ghostly Prison", "oracle_text": "Creatures can't attack you..."}]
    prefs = JankPreferences(synergy_first=True)
    prompt = build_recommendation_prompt(
        concept="Pillow fort control", cards=cards, preferences=prefs
    )
    assert "Ghostly Prison" in prompt
    assert "Pillow fort control" in prompt

def test_synergy_first_preference_in_prompt():
    prefs = JankPreferences(synergy_first=True, hidden_gems=False)
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "synergy" in prompt.lower()

def test_hidden_gems_preference_in_prompt():
    prefs = JankPreferences(hidden_gems=True, synergy_first=False)
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "underplayed" in prompt.lower() or "hidden" in prompt.lower()

def test_chaos_injection_preference_in_prompt():
    prefs = JankPreferences(chaos_injection=True)
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "off-meta" in prompt.lower() or "jank" in prompt.lower()
```

**Step 2: Run failing tests**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: ImportError.

**Step 3: Create prompt_builder.py**

```python
# backend/services/prompt_builder.py
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

def build_recommendation_prompt(
    concept: str,
    cards: list[dict],
    preferences: JankPreferences,
    existing_deck: list[dict] | None = None,
) -> str:
    card_block = "\n".join(
        f"{i+1}. {c['name']} | {c.get('mana_cost','')} | {c.get('type_line','')}\n   {c.get('oracle_text','')}"
        for i, c in enumerate(cards)
    ) or "No card context provided."

    deck_block = ""
    if existing_deck:
        deck_block = "\n\nCURRENT DECK:\n" + "\n".join(
            f"- {c['quantity']}x {c['name']}" for c in existing_deck
        )

    pref_block = _pref_instructions(preferences)

    return f"""You are an expert Magic: The Gathering deck builder who loves finding creative, unusual synergies.

DECK CONCEPT: {concept}
{deck_block}

RECOMMENDATION STYLE (follow these instructions strictly):
{pref_block}

AVAILABLE CARD CONTEXT (use this — do not invent cards):
{card_block}

Based on the deck concept and the cards listed above, recommend 10 cards that would strengthen this deck.
For each card provide:
1. Card name (must be from the list above)
2. Why it fits the concept
3. What synergy or interaction makes it interesting

Do NOT recommend cards based on how popular they are. Do NOT just list staples.
Format your response as a numbered list."""
```

**Step 4: Create ollama_client.py**

```python
# backend/services/ollama_client.py
import ollama

async def generate_recommendations(prompt: str, model: str = "llama3") -> str:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]
```

**Step 5: Run prompt builder tests**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add backend/services/ollama_client.py backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat: add Ollama client and RAG prompt builder with jank preferences"
```

---

## Task 5: Pydantic Models

**Files:**
- Create: `backend/models/deck.py`
- Create: `backend/models/recommendation.py`

**Step 1: Create deck.py**

```python
# backend/models/deck.py
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

class RecommendRequest(BaseModel):
    concept: str
    color_identity: list[str] = []
    existing_deck: list[Card] = []
    synergy_first: bool = False
    hidden_gems: bool = False
    chaos_injection: bool = False
    llm_choice: bool = False
    model: str = "llama3"
```

**Step 2: Create recommendation.py**

```python
# backend/models/recommendation.py
from pydantic import BaseModel

class CardRecommendation(BaseModel):
    name: str
    reasoning: str
    image_uri: str | None = None

class RecommendResponse(BaseModel):
    recommendations_text: str
    cards_used_as_context: list[str]
```

**Step 3: Commit**

```bash
git add backend/models/
git commit -m "feat: add Pydantic request/response models"
```

---

## Task 6: FastAPI Routers

**Files:**
- Create: `backend/routers/recommend.py`
- Create: `backend/routers/import_deck.py`
- Create: `backend/routers/cards.py`
- Modify: `backend/main.py`

**Step 1: Create recommend.py router**

```python
# backend/routers/recommend.py
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
    query = f"c:{color_filter}" if color_filter else "f:commander"
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
    result = await generate_recommendations(prompt=prompt, model=req.model)
    return RecommendResponse(
        recommendations_text=result,
        cards_used_as_context=[c["name"] for c in cards],
    )
```

**Step 2: Create import_deck.py router**

```python
# backend/routers/import_deck.py
from fastapi import APIRouter, HTTPException
from models.deck import DeckImportRequest, DeckImportResponse
from services.archidekt_client import fetch_deck

router = APIRouter(prefix="/api", tags=["import"])

@router.post("/import/archidekt", response_model=DeckImportResponse)
async def import_archidekt(req: DeckImportRequest):
    deck = await fetch_deck(req.archidekt_url)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or is private")
    return DeckImportResponse(**deck)
```

**Step 3: Create cards.py router**

```python
# backend/routers/cards.py
from fastapi import APIRouter, HTTPException
from services.scryfall_client import get_card_by_name

router = APIRouter(prefix="/api", tags=["cards"])

@router.get("/card/{name}")
async def card_lookup(name: str):
    card = await get_card_by_name(name)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card
```

**Step 4: Update main.py to register routers**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import recommend, import_deck, cards

app = FastAPI(title="MTG Deck Advisor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend.router)
app.include_router(import_deck.router)
app.include_router(cards.router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 5: Start the server and verify all routes appear**

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` — all routes should be visible in the Swagger UI.

**Step 6: Commit**

```bash
git add backend/routers/ backend/main.py
git commit -m "feat: add FastAPI routers for recommend, import, and card lookup"
```

---

## Task 7: React + Vite Frontend Scaffold

**Files:**
- Create: `frontend/` (via Vite scaffolding)

**Step 1: Scaffold the React + TypeScript app**

```bash
cd C:\Users\ndelle432@cable.comcast.com\Documents\mtg-deck-advisor
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install Tailwind CSS**

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Update `tailwind.config.js`:

```js
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

Add to `src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 3: Verify dev server starts**

```bash
npm run dev
```

Expected: Vite dev server at `http://localhost:5173`

**Step 4: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold React + TypeScript frontend with Tailwind"
```

---

## Task 8: Frontend API Client

**Files:**
- Create: `frontend/src/api/client.ts`

**Step 1: Create the typed API client**

```typescript
// frontend/src/api/client.ts
const BASE = "http://localhost:8000/api";

export interface JankPreferences {
  synergy_first: boolean;
  hidden_gems: boolean;
  chaos_injection: boolean;
  llm_choice: boolean;
}

export interface RecommendRequest {
  concept: string;
  color_identity: string[];
  existing_deck: { name: string; quantity: number }[];
  model: string;
  preferences: JankPreferences;
}

export interface RecommendResponse {
  recommendations_text: string;
  cards_used_as_context: string[];
}

export interface DeckCard {
  name: string;
  quantity: number;
  category: string;
}

export interface ImportedDeck {
  name: string;
  format: string;
  cards: DeckCard[];
}

export async function importArchidektDeck(url: string): Promise<ImportedDeck> {
  const res = await fetch(`${BASE}/import/archidekt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ archidekt_url: url }),
  });
  if (!res.ok) throw new Error(`Import failed: ${res.statusText}`);
  return res.json();
}

export async function getRecommendations(
  req: RecommendRequest
): Promise<RecommendResponse> {
  const res = await fetch(`${BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      concept: req.concept,
      color_identity: req.color_identity,
      existing_deck: req.existing_deck,
      model: req.model,
      synergy_first: req.preferences.synergy_first,
      hidden_gems: req.preferences.hidden_gems,
      chaos_injection: req.preferences.chaos_injection,
      llm_choice: req.preferences.llm_choice,
    }),
  });
  if (!res.ok) throw new Error(`Recommendation failed: ${res.statusText}`);
  return res.json();
}

export async function lookupCard(name: string) {
  const res = await fetch(`${BASE}/card/${encodeURIComponent(name)}`);
  if (!res.ok) return null;
  return res.json();
}
```

**Step 2: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add typed TypeScript API client"
```

---

## Task 9: JankPreferences Component

**Files:**
- Create: `frontend/src/components/JankPreferences.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/JankPreferences.tsx
import type { JankPreferences } from "../api/client";

interface Props {
  prefs: JankPreferences;
  onChange: (prefs: JankPreferences) => void;
}

const OPTIONS: { key: keyof JankPreferences; label: string; description: string }[] = [
  {
    key: "synergy_first",
    label: "Synergy-First",
    description: "Find mechanical synergies from oracle text. Ignores card popularity entirely.",
  },
  {
    key: "hidden_gems",
    label: "Hidden Gems",
    description: "Surface underplayed cards most players overlook but that synergize well.",
  },
  {
    key: "chaos_injection",
    label: "Chaos Injection",
    description: "Deliberately include off-meta, jank, or meme-worthy cards that still advance the theme.",
  },
  {
    key: "llm_choice",
    label: "LLM's Choice",
    description: "Let the AI blend all of the above based on what makes the deck most interesting.",
  },
];

export function JankPreferences({ prefs, onChange }: Props) {
  const toggle = (key: keyof JankPreferences) => {
    onChange({ ...prefs, [key]: !prefs[key] });
  };

  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-sm text-gray-700 uppercase tracking-wide">
        Recommendation Style
      </h3>
      {OPTIONS.map(({ key, label, description }) => (
        <label key={key} className="flex items-start gap-3 cursor-pointer group">
          <input
            type="checkbox"
            checked={prefs[key]}
            onChange={() => toggle(key)}
            className="mt-1 accent-indigo-600"
          />
          <div>
            <span className="font-medium text-sm">{label}</span>
            <p className="text-xs text-gray-500">{description}</p>
          </div>
        </label>
      ))}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/JankPreferences.tsx
git commit -m "feat: add JankPreferences checkbox component"
```

---

## Task 10: DeckEditor Component

**Files:**
- Create: `frontend/src/components/DeckEditor.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/DeckEditor.tsx
import { useState } from "react";
import { importArchidektDeck } from "../api/client";
import type { DeckCard } from "../api/client";

interface Props {
  cards: DeckCard[];
  onCardsChange: (cards: DeckCard[]) => void;
}

export function DeckEditor({ cards, onCardsChange }: Props) {
  const [urlInput, setUrlInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deckName, setDeckName] = useState("");

  const handleImport = async () => {
    setLoading(true);
    setError(null);
    try {
      const deck = await importArchidektDeck(urlInput);
      setDeckName(deck.name);
      onCardsChange(deck.cards);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold">Deck</h2>
        {deckName && <p className="text-sm text-gray-500">{deckName}</p>}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Archidekt deck URL or ID"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button
          onClick={handleImport}
          disabled={loading || !urlInput}
          className="bg-indigo-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
        >
          {loading ? "Importing..." : "Import"}
        </button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {cards.length > 0 && (
        <div className="max-h-64 overflow-y-auto border rounded p-2 space-y-1">
          {cards.map((card, i) => (
            <div key={i} className="flex justify-between text-sm">
              <span>{card.name}</span>
              <span className="text-gray-400">x{card.quantity}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/DeckEditor.tsx
git commit -m "feat: add DeckEditor component with Archidekt import"
```

---

## Task 11: RecommendationPanel Component

**Files:**
- Create: `frontend/src/components/RecommendationPanel.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/RecommendationPanel.tsx
interface Props {
  text: string;
  contextCards: string[];
}

export function RecommendationPanel({ text, contextCards }: Props) {
  if (!text) return null;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold">Recommendations</h2>
      <pre className="whitespace-pre-wrap text-sm bg-gray-50 border rounded p-4 leading-relaxed">
        {text}
      </pre>
      {contextCards.length > 0 && (
        <details className="text-xs text-gray-400">
          <summary className="cursor-pointer">
            Cards used as context ({contextCards.length})
          </summary>
          <ul className="mt-1 space-y-0.5">
            {contextCards.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/RecommendationPanel.tsx
git commit -m "feat: add RecommendationPanel component"
```

---

## Task 12: Home Page — Wire Everything Together

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/Home.tsx`

**Step 1: Create Home.tsx**

```tsx
// frontend/src/pages/Home.tsx
import { useState } from "react";
import { DeckEditor } from "../components/DeckEditor";
import { JankPreferences } from "../components/JankPreferences";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { getRecommendations } from "../api/client";
import type { DeckCard, JankPreferences as JankPrefs } from "../api/client";

const MTG_COLORS = ["W", "U", "B", "R", "G"];
const COLOR_LABELS: Record<string, string> = {
  W: "White", U: "Blue", B: "Black", R: "Red", G: "Green",
};

export function Home() {
  const [cards, setCards] = useState<DeckCard[]>([]);
  const [concept, setConcept] = useState("");
  const [colorIdentity, setColorIdentity] = useState<string[]>([]);
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

  const toggleColor = (c: string) =>
    setColorIdentity((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );

  const handleRecommend = async () => {
    if (!concept.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getRecommendations({
        concept,
        color_identity: colorIdentity,
        existing_deck: cards,
        model,
        preferences: prefs,
      });
      setResult({ text: res.recommendations_text, context: res.cards_used_as_context });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-5xl mx-auto space-y-6">
        <header>
          <h1 className="text-3xl font-bold text-indigo-700">MTG Deck Advisor</h1>
          <p className="text-gray-500 text-sm mt-1">
            Open-source LLM-powered deck recommendations. Zero EDHREC bias.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left panel */}
          <div className="bg-white rounded-xl shadow p-6 space-y-6">
            <DeckEditor cards={cards} onCardsChange={setCards} />

            <div>
              <label className="block font-semibold text-sm mb-1">Deck Concept</label>
              <textarea
                rows={3}
                placeholder="Describe your deck idea, e.g. 'Simic ramp that wins through weird creature combat'"
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block font-semibold text-sm mb-2">Color Identity</label>
              <div className="flex gap-2">
                {MTG_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => toggleColor(c)}
                    className={`px-3 py-1 rounded text-sm border ${
                      colorIdentity.includes(c)
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-white text-gray-700 border-gray-300"
                    }`}
                  >
                    {COLOR_LABELS[c]}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block font-semibold text-sm mb-1">Ollama Model</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            <JankPreferences prefs={prefs} onChange={setPrefs} />

            <button
              onClick={handleRecommend}
              disabled={loading || !concept.trim()}
              className="w-full bg-indigo-600 text-white py-2 rounded font-semibold disabled:opacity-50"
            >
              {loading ? "Thinking..." : "Get Recommendations"}
            </button>

            {error && <p className="text-red-500 text-sm">{error}</p>}
          </div>

          {/* Right panel */}
          <div className="bg-white rounded-xl shadow p-6">
            {result ? (
              <RecommendationPanel text={result.text} contextCards={result.context} />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                Recommendations will appear here
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Update App.tsx**

```tsx
// frontend/src/App.tsx
import { Home } from "./pages/Home";

function App() {
  return <Home />;
}

export default App;
```

**Step 3: Run the frontend and verify the UI renders**

```bash
cd frontend
npm run dev
```

Expected: Full UI at `http://localhost:5173` with deck editor, color toggles, jank checkboxes, and recommendation panel.

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: wire up Home page with all components"
```

---

## Task 13: End-to-End Smoke Test

**Prerequisite:** Ollama is running locally with a model pulled (e.g. `ollama pull llama3`).

**Step 1: Start the backend**

```bash
cd backend
.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Step 2: Start the frontend**

```bash
cd frontend
npm run dev
```

**Step 3: Manual smoke test**

1. Open `http://localhost:5173`
2. Enter concept: "Grixis spellslinger that copies instants and sorceries"
3. Select Black, Blue, Red as color identity
4. Check "Chaos Injection" and "Synergy-First"
5. Click "Get Recommendations"
6. Verify recommendations appear with card names and reasoning
7. Paste a public Archidekt deck URL and click Import
8. Verify the deck card list populates
9. Click Get Recommendations again — verify context reflects imported deck

**Step 4: Final commit**

```bash
git add .
git commit -m "chore: complete e2e smoke test and finalize v1"
```

---

## Prerequisites Checklist

Before beginning implementation verify these are installed:

- [ ] Python 3.11+: `python --version`
- [ ] Node.js 20+: `node --version`
- [ ] Ollama installed and running: `ollama --version`
- [ ] At least one model pulled: `ollama list` (recommended: `ollama pull llama3`)
- [ ] Git: `git --version`
