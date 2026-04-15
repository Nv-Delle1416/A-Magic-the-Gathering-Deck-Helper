import pytest
from services.scryfall_client import search_cards, get_card_by_name

@pytest.mark.asyncio
async def test_search_cards_returns_list():
    results = await search_cards(query="o:flying c:W", limit=5)
    assert isinstance(results, list)
    assert len(results) <= 5
    assert len(results) > 0
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
