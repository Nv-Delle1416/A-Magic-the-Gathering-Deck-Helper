from pydantic import BaseModel


class JankPreferences(BaseModel):
    synergy_first: bool = False
    hidden_gems: bool = False
    chaos_injection: bool = False
    llm_choice: bool = False


def _pref_instructions(prefs: JankPreferences) -> str:
    parts = []
    if prefs.synergy_first:
        parts.append(
            "- SYNERGY-FIRST: Focus exclusively on mechanical synergies found in oracle text. "
            "Ignore card popularity entirely. Identify keyword interactions, unusual triggers, "
            "and combo potential."
        )
    if prefs.hidden_gems:
        parts.append(
            "- HIDDEN GEMS: Prioritize cards that are underplayed and rarely seen in decklists. "
            "Surface cards that most players overlook but that have strong synergy with the deck concept."
        )
    if prefs.chaos_injection:
        parts.append(
            "- CHAOS INJECTION: Deliberately include some off-meta, jank, or meme-worthy cards "
            "that are surprising but still advance the theme. Embrace the weird."
        )
    if prefs.llm_choice or not parts:
        parts.append(
            "- Use your own judgment to blend synergy discovery, hidden gems, and creative chaos "
            "based on what would make this deck the most interesting to play."
        )
    return "\n".join(parts)


def build_recommendation_prompt(
    concept: str,
    cards: list[dict],
    preferences: JankPreferences,
    existing_deck: list[dict] | None = None,
) -> str:
    card_block = "\n".join(
        f"{i+1}. {c.get('name', 'Unknown')} | {c.get('mana_cost','')} | {c.get('type_line','')}\n   {c.get('oracle_text','').replace(chr(10), ' ')}"
        for i, c in enumerate(cards)
    ) or "No card context provided."

    deck_block = ""
    if existing_deck:
        deck_block = "\n\nCURRENT DECK:\n" + "\n".join(
            f"- {c['quantity']}x {c['name']}" for c in existing_deck
        )

    pref_block = _pref_instructions(preferences)

    return f"""You are an expert Magic: The Gathering deck builder who loves finding creative, unusual synergies.

DECK CONCEPT: {concept}
{deck_block}

RECOMMENDATION STYLE (follow these instructions strictly):
{pref_block}

AVAILABLE CARD CONTEXT (use this — do not invent cards):
{card_block}

Based on the deck concept and the cards listed above, recommend 10 cards that would strengthen this deck.
For each card provide:
1. Card name (must be from the list above)
2. Why it fits the concept
3. What synergy or interaction makes it interesting

Do NOT recommend cards based on how popular they are. Do NOT just list staples.
Format your response as a numbered list."""
