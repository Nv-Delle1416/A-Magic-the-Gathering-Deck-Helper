from services.prompt_builder import build_recommendation_prompt, JankPreferences


def test_prompt_includes_card_context():
    cards = [{"name": "Ghostly Prison", "oracle_text": "Creatures can't attack you..."}]
    prefs = JankPreferences(synergy_first=True)
    prompt = build_recommendation_prompt(
        concept="Pillow fort control", cards=cards, preferences=prefs
    )
    assert "Ghostly Prison" in prompt
    assert "Pillow fort control" in prompt


def test_synergy_first_preference_in_prompt():
    prefs = JankPreferences(synergy_first=True, hidden_gems=False)
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "synergy" in prompt.lower()


def test_hidden_gems_preference_in_prompt():
    prefs = JankPreferences(hidden_gems=True, synergy_first=False)
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "underplayed" in prompt.lower() or "hidden" in prompt.lower()


def test_chaos_injection_preference_in_prompt():
    prefs = JankPreferences(chaos_injection=True)
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "off-meta" in prompt.lower() or "jank" in prompt.lower()


def test_existing_deck_included_in_prompt():
    existing = [{"name": "Sol Ring", "quantity": 1}, {"name": "Command Tower", "quantity": 1}]
    prefs = JankPreferences()
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs, existing_deck=existing)
    assert "Sol Ring" in prompt
    assert "Command Tower" in prompt
    assert "CURRENT DECK" in prompt


def test_all_flags_false_uses_llm_choice_fallback():
    prefs = JankPreferences()  # all False
    prompt = build_recommendation_prompt(concept="Test", cards=[], preferences=prefs)
    assert "judgment" in prompt.lower() or "blend" in prompt.lower()
