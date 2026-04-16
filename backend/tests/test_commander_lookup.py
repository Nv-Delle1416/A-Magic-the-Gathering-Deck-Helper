import pytest
from unittest.mock import AsyncMock, patch
from services.scryfall_client import get_commander


@pytest.mark.asyncio
async def test_get_commander_valid():
    result = await get_commander("Atraxa, Praetors' Voice")
    assert result is not None
    assert result["name"] == "Atraxa, Praetors' Voice"
    assert "W" in result["color_identity"]
    assert "B" in result["color_identity"]
    assert "G" in result["color_identity"]
    assert "U" in result["color_identity"]


@pytest.mark.asyncio
async def test_get_commander_nonexistent():
    result = await get_commander("zzzznotacard12345")
    assert result is None


@pytest.mark.asyncio
async def test_get_commander_non_legendary_creature_returns_none():
    # Lightning Bolt is not a legal commander
    result = await get_commander("Lightning Bolt")
    assert result is None


@pytest.mark.asyncio
async def test_get_commander_can_be_commander_oracle_text():
    # No card in the current Scryfall oracle has "can be your commander" in its
    # oracle_text (Grist's oracle was updated and the text was removed). We mock
    # get_card_by_name to return a card whose oracle text contains that phrase,
    # exercising the can_be_commander code branch in get_commander.
    fake_card = {
        "name": "Grist, the Hunger Tide",
        "mana_cost": "{1}{B}{G}",
        "type_line": "Legendary Planeswalker — Grist",
        "oracle_text": "As long as Grist, the Hunger Tide isn't on the battlefield, it's a 1/1 Insect creature.\nGrist, the Hunger Tide can be your commander.",
        "color_identity": ["B", "G"],
        "edhrec_rank": 100,
        "image_uri": None,
    }
    with patch("services.scryfall_client.get_card_by_name", new=AsyncMock(return_value=fake_card)):
        result = await get_commander("Grist, the Hunger Tide")
    assert result is not None
    assert "Grist" in result["name"]
    assert "can be your commander" in result["oracle_text"].lower()
