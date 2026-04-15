# MTG Deck Advisor

An AI-powered Magic: The Gathering deck advisor backed by a FastAPI backend and a React frontend.

## Structure

```
mtg-deck-advisor/
├── backend/      # FastAPI Python backend
├── frontend/     # React frontend
└── docs/         # Design documents
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Running the End-to-End Smoke Test

The full recommendation flow requires Ollama to run inference locally, which can take several minutes on a CPU-only machine. Run these steps manually after starting both the backend and Ollama.

### 1. Start Ollama (if not already running)

Ollama is not on the system PATH — call it via full path:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
```

Confirm available models (tinyllama is faster than llama3 on CPU):

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

If `tinyllama` is not listed, pull it first:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull tinyllama
```

### 2. Start the backend

```powershell
cd backend
.venv\Scripts\activate
uvicorn main:app --reload
```

### 3. Verify health and supporting endpoints

```powershell
# Health check
Invoke-RestMethod http://localhost:8000/health

# Card lookup (Scryfall)
Invoke-RestMethod http://localhost:8000/api/card/Sol%20Ring | ConvertTo-Json

# Deck import (Archidekt deck ID 300000 — known-good public deck)
$body = '{"deck_id": "300000"}' 
Invoke-RestMethod -Uri http://localhost:8000/api/import/archidekt -Method POST -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 5
```

### 4. Run the full recommendation smoke test

This step calls Ollama and **will take several minutes** on CPU. Use `tinyllama` for the fastest result.

```powershell
$body = @{
    color_identity     = @("B", "R", "U")
    concept            = "sacrifice value engine"
    jank_preferences   = @{
        synergy_first   = $true
        hidden_gems     = $true
        chaos_injection = $false
        llm_choice      = $false
    }
    model         = "tinyllama"
    existing_deck = @()
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
    -Uri         http://localhost:8000/api/recommend `
    -Method      POST `
    -ContentType "application/json" `
    -Body        $body | ConvertTo-Json -Depth 10
```

Expected: a JSON object with a `recommendations` array, each entry containing `name`, `reason`, and `mana_cost`.

> **Note:** If the request times out in your terminal, increase the timeout or wait longer — the backend keeps processing even if the client disconnects. Check the uvicorn console for progress.
