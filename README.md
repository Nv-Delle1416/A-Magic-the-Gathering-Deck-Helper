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
