import pytest
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
