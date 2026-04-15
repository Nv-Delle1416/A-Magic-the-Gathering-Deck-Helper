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
