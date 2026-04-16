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


def build_query_generation_prompt(
    concept: str,
    commander: dict,
    existing_deck: list[dict] | None = None,
    preferences: JankPreferences | None = None,
) -> str:
    """Pass 1 prompt: ask the LLM to analyze the deck and generate Scryfall queries."""
    deck_block = ""
    if existing_deck:
        deck_block = "\n\nCURRENT DECK:\n" + "\n".join(
            f"- {c['quantity']}x {c['name']}" for c in existing_deck
        )

    pref_block = ""
    if preferences:
        pref_instructions = []
        if preferences.hidden_gems:
            pref_instructions.append(
                "- HIDDEN GEMS: Generate queries that target obscure or rarely-played cards. "
                "Avoid common staples; surface cards most players overlook."
            )
        if preferences.chaos_injection:
            pref_instructions.append(
                "- CHAOS INJECTION: Include at least one query designed to find off-meta, "
                "weird, or jank cards that could still advance the deck's theme."
            )
        if preferences.synergy_first:
            pref_instructions.append(
                "- SYNERGY-FIRST: Bias queries toward oracle text searches that capture "
                "mechanical interactions and keyword synergies."
            )
        if pref_instructions:
            pref_block = "\n\nQUERY STYLE PREFERENCES (follow strictly):\n" + "\n".join(pref_instructions)

    return f"""You are an expert Magic: The Gathering deck builder and Scryfall power user.

COMMANDER: {commander.get('name', '')}
Type: {commander.get('type_line', '')}
Oracle Text: {commander.get('oracle_text', '')}
Color Identity: {', '.join(commander.get('color_identity', []))}
{deck_block}{pref_block}

DECK CONCEPT: {concept}

Your task:
1. Analyze the deck concept and commander to identify: key themes, mechanics, and win conditions.
2. If a current deck is provided, identify specific gaps: missing ramp, card draw, removal, synergy payoffs, or anything that weakens the strategy.
3. Generate 5 to 8 Scryfall search query strings that would surface cards filling those gaps or advancing those themes. Write only the oracle/type search portion — do NOT include color identity or format filters (those are added automatically).

Example queries:
- o:"proliferate" t:artifact
- o:"counter" o:"draw a card"
- t:enchantment o:"whenever a creature"
- o:"sacrifice" o:"token"

Respond ONLY with a JSON object in this exact format (no markdown, no explanation outside the JSON):
{{
  "analysis": "A short paragraph summarizing the deck themes and gaps identified.",
  "queries": [
    "query string 1",
    "query string 2"
  ]
}}"""


def build_selection_prompt(
    concept: str,
    commander: dict,
    deck_analysis: str,
    candidates: list[dict],
    preferences: JankPreferences,
    existing_deck: list[dict] | None = None,
) -> str:
    """Pass 2 prompt: ask the LLM to select 10 cards from the candidate pool."""
    card_block = "\n".join(
        f"{i+1}. {c.get('name', 'Unknown')} | {c.get('mana_cost', '')} | {c.get('type_line', '')}\n"
        f"   {c.get('oracle_text', '').replace(chr(10), ' ')}"
        for i, c in enumerate(candidates)
    ) or "No card context provided."

    deck_block = ""
    if existing_deck:
        deck_block = "\n\nCURRENT DECK:\n" + "\n".join(
            f"- {c['quantity']}x {c['name']}" for c in existing_deck
        )

    pref_block = _pref_instructions(preferences)

    return f"""You are an expert Magic: The Gathering deck builder who loves finding creative, unusual synergies.

COMMANDER: {commander.get('name', '')} — {commander.get('oracle_text', '')}
DECK CONCEPT: {concept}
{deck_block}

DECK ANALYSIS (your prior assessment of themes and gaps):
{deck_analysis}

RECOMMENDATION STYLE (follow these instructions strictly):
{pref_block}

AVAILABLE CARDS (all are legal in Commander for this color identity — do not recommend cards outside this list):
{card_block}

Select exactly 10 cards from the list above that best address the identified gaps and advance the deck's themes.
For each card provide:
1. Card name (must be from the list above)
2. Which specific gap or theme this card addresses
3. The synergy or interaction that makes it interesting for this deck

Do NOT justify a card by describing what it does in isolation. Every recommendation must reference a specific gap or interaction with the commander or deck strategy.
Do NOT recommend cards based on how popular they are. Do NOT list staples without synergy reasoning.
Format your response as a numbered list."""
