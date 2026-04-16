from services.prompt_builder import (
    JankPreferences,
    build_query_generation_prompt,
    build_selection_prompt,
)


# --- Pass 1: query generation prompt ---

def test_query_generation_includes_concept():
    commander = {
        "name": "Atraxa, Praetors' Voice",
        "type_line": "Legendary Creature — Phyrexian Angel Horror",
        "oracle_text": "Flying, vigilance, deathtouch, lifelink. At the beginning of your end step, proliferate.",
        "color_identity": ["W", "U", "B", "G"],
        "mana_cost": "{G}{W}{U}{B}",
    }
    prompt = build_query_generation_prompt(
        concept="Atraxa proliferate counters", commander=commander
    )
    assert "Atraxa" in prompt
    assert "proliferate counters" in prompt


def test_query_generation_includes_existing_deck():
    commander = {
        "name": "Atraxa, Praetors' Voice",
        "type_line": "Legendary Creature",
        "oracle_text": "proliferate",
        "color_identity": ["W", "U", "B", "G"],
        "mana_cost": "{G}{W}{U}{B}",
    }
    existing = [{"name": "Sol Ring", "quantity": 1}, {"name": "Sword of Truth and Justice", "quantity": 1}]
    prompt = build_query_generation_prompt(
        concept="Counters", commander=commander, existing_deck=existing
    )
    assert "Sol Ring" in prompt
    assert "Sword of Truth and Justice" in prompt


def test_query_generation_requests_json_output():
    commander = {
        "name": "Test Commander",
        "type_line": "Legendary Creature",
        "oracle_text": "",
        "color_identity": ["R"],
        "mana_cost": "{R}",
    }
    prompt = build_query_generation_prompt(concept="Test", commander=commander)
    assert "json" in prompt.lower()
    assert "queries" in prompt.lower()
    assert "analysis" in prompt.lower()


# --- Pass 2: selection prompt ---

def test_selection_prompt_includes_candidates():
    commander = {
        "name": "Atraxa, Praetors' Voice",
        "type_line": "Legendary Creature",
        "oracle_text": "proliferate",
        "color_identity": ["W", "U", "B", "G"],
        "mana_cost": "{G}{W}{U}{B}",
    }
    candidates = [
        {"name": "Contagion Engine", "mana_cost": "{6}", "type_line": "Artifact",
         "oracle_text": "When Contagion Engine enters, proliferate. At the beginning of your end step, proliferate."},
    ]
    prefs = JankPreferences(synergy_first=True)
    prompt = build_selection_prompt(
        concept="Proliferate counters",
        commander=commander,
        deck_analysis="Deck needs more proliferate enablers.",
        candidates=candidates,
        preferences=prefs,
    )
    assert "Contagion Engine" in prompt
    assert "Proliferate counters" in prompt
    assert "10" in prompt  # ask for 10 recommendations


def test_selection_prompt_includes_deck_analysis():
    commander = {
        "name": "Test",
        "type_line": "Legendary Creature",
        "oracle_text": "",
        "color_identity": ["R"],
        "mana_cost": "{R}",
    }
    prefs = JankPreferences()
    prompt = build_selection_prompt(
        concept="Test",
        commander=commander,
        deck_analysis="Missing ramp and draw.",
        candidates=[],
        preferences=prefs,
    )
    assert "Missing ramp and draw." in prompt


def test_selection_prompt_synergy_first_preference():
    commander = {
        "name": "Test",
        "type_line": "Legendary Creature",
        "oracle_text": "",
        "color_identity": ["R"],
        "mana_cost": "{R}",
    }
    prefs = JankPreferences(synergy_first=True)
    prompt = build_selection_prompt(
        concept="Test", commander=commander, deck_analysis="",
        candidates=[], preferences=prefs
    )
    assert "synergy" in prompt.lower()
