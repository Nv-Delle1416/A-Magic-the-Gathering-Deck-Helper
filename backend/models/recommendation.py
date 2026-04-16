from pydantic import BaseModel


class RecommendResponse(BaseModel):
    recommendations_text: str
    cards_used_as_context: list[str]
