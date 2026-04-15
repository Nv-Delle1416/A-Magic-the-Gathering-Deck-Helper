import pytest
from services.archidekt_client import fetch_deck


@pytest.mark.asyncio
async def test_fetch_deck_returns_card_list():
    # Deck 300000 is a known public Archidekt deck "Thantis the SweaterWearing"
    result = await fetch_deck("300000")
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
