const BASE = "http://localhost:8000/api";

export interface JankPreferences {
  synergy_first: boolean;
  hidden_gems: boolean;
  chaos_injection: boolean;
  llm_choice: boolean;
}

export interface RecommendRequest {
  concept: string;
  color_identity: string[];
  existing_deck: { name: string; quantity: number }[];
  model: string;
  preferences: JankPreferences;
}

export interface RecommendResponse {
  recommendations_text: string;
  cards_used_as_context: string[];
}

export interface DeckCard {
  name: string;
  quantity: number;
  category: string;
}

export interface ImportedDeck {
  name: string;
  format: string;
  cards: DeckCard[];
}

export async function importArchidektDeck(url: string): Promise<ImportedDeck> {
  const res = await fetch(`${BASE}/import/archidekt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ archidekt_url: url }),
  });
  if (!res.ok) throw new Error(`Import failed: ${res.statusText}`);
  return res.json();
}

export async function getRecommendations(
  req: RecommendRequest
): Promise<RecommendResponse> {
  const res = await fetch(`${BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      concept: req.concept,
      color_identity: req.color_identity,
      existing_deck: req.existing_deck,
      model: req.model,
      synergy_first: req.preferences.synergy_first,
      hidden_gems: req.preferences.hidden_gems,
      chaos_injection: req.preferences.chaos_injection,
      llm_choice: req.preferences.llm_choice,
    }),
  });
  if (!res.ok) throw new Error(`Recommendation failed: ${res.statusText}`);
  return res.json();
}

export interface CardDetail {
  name: string;
  mana_cost: string;
  type_line: string;
  oracle_text: string;
  color_identity: string[];
  edhrec_rank: number | null;
  image_uri: string | null;
}

export async function lookupCard(name: string): Promise<CardDetail | null> {
  const res = await fetch(`${BASE}/card/${encodeURIComponent(name)}`);
  if (!res.ok) return null;
  return res.json();
}
