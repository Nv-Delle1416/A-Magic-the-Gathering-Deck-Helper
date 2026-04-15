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
