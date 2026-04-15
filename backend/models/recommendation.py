from pydantic import BaseModel

class CardRecommendation(BaseModel):
    name: str
    reasoning: str
    image_uri: str | None = None

class RecommendResponse(BaseModel):
    recommendations_text: str
    cards_used_as_context: list[str]
