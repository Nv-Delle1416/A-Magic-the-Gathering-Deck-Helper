import httpx
from typing import Optional

SCRYFALL_BASE = "https://api.scryfall.com"


def _slim_card(card: dict) -> dict:
    """Extract only the fields we need to keep prompt context small."""
    return {
        "name": card.get("name", ""),
        "mana_cost": card.get("mana_cost") or card.get("card_faces", [{}])[0].get("mana_cost", ""),
        "type_line": card.get("type_line", ""),
        "oracle_text": card.get("oracle_text", card.get("card_faces", [{}])[0].get("oracle_text", "")),
        "color_identity": card.get("color_identity", []),
        "edhrec_rank": card.get("edhrec_rank"),
        "image_uri": card.get("image_uris", {}).get("normal") or card.get("card_faces", [{}])[0].get("image_uris", {}).get("normal"),
    }


async def search_cards(query: str, limit: int = 20) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SCRYFALL_BASE}/cards/search",
                params={"q": query, "order": "edhrec", "dir": "desc"},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            cards = data.get("data", [])[:limit]
            return [_slim_card(c) for c in cards]
    except httpx.HTTPError:
        return []


async def get_card_by_name(name: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SCRYFALL_BASE}/cards/named",
                params={"fuzzy": name},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            return _slim_card(resp.json())
    except httpx.HTTPError:
        return None
