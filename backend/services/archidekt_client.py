import re
import httpx
from typing import Optional

ARCHIDEKT_BASE = "https://archidekt.com/api"

FORMAT_MAP = {
    1: "Standard",
    2: "Modern",
    3: "Commander",
    4: "Legacy",
    5: "Vintage",
    6: "Pauper",
    7: "Pioneer",
    8: "Brawl",
    9: "Historic",
    10: "Penny Dreadful",
}


def extract_deck_id(url_or_id: str) -> str:
    """Extract numeric deck ID from a full Archidekt URL or a plain ID string."""
    match = re.search(r"/decks/(\d+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()


async def fetch_deck(url_or_id: str) -> Optional[dict]:
    deck_id = extract_deck_id(url_or_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{ARCHIDEKT_BASE}/decks/{deck_id}/",
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            cards = []
            for card in data.get("cards", []):
                try:
                    name = card["card"]["oracleCard"]["name"]
                except (KeyError, TypeError):
                    continue  # skip malformed card entries
                cards.append({
                    "name": name,
                    "quantity": card.get("quantity", 1),
                    "category": card.get("categories", ["Mainboard"])[0]
                    if card.get("categories")
                    else "Mainboard",
                })
            raw_format = data.get("deckFormat", "Unknown")
            readable_format = FORMAT_MAP.get(raw_format, str(raw_format))
            return {
                "name": data.get("name", "Imported Deck"),
                "format": readable_format,
                "cards": cards,
            }
    except (httpx.HTTPError, Exception):
        return None
