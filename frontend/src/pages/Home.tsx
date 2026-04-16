import { useState } from "react";
import { DeckEditor } from "../components/DeckEditor";
import { JankPreferences } from "../components/JankPreferences";
import type { JankPreferences as JankPrefs } from "../components/JankPreferences";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { getRecommendations } from "../api/client";
import type { DeckCard } from "../api/client";

export function Home() {
  const [cards, setCards] = useState<DeckCard[]>([]);
  const [concept, setConcept] = useState("");
  const [commanderName, setCommanderName] = useState("");
  const [prefs, setPrefs] = useState<JankPrefs>({
    synergy_first: false,
    hidden_gems: false,
    chaos_injection: false,
    llm_choice: true,
  });
  const [model, setModel] = useState("llama3");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ text: string; context: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRecommend = async () => {
    if (!concept.trim() || !commanderName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getRecommendations({
        concept,
        commander_name: commanderName,
        existing_deck: cards,
        model,
        synergy_first: prefs.synergy_first,
        hidden_gems: prefs.hidden_gems,
        chaos_injection: prefs.chaos_injection,
        llm_choice: prefs.llm_choice,
      });
      setResult({ text: res.recommendations_text, context: res.cards_used_as_context });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-5xl mx-auto space-y-6">
        <header>
          <h1 className="text-3xl font-bold text-indigo-700">MTG Deck Advisor</h1>
          <p className="text-gray-500 text-sm mt-1">
            Open-source LLM-powered deck recommendations. Zero EDHREC bias.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left panel */}
          <div className="bg-white rounded-xl shadow p-6 space-y-6">
            <DeckEditor cards={cards} onCardsChange={setCards} />

            <div>
              <label className="block font-semibold text-sm mb-1">Deck Concept</label>
              <textarea
                rows={3}
                placeholder="Describe your deck idea, e.g. 'Simic ramp that wins through weird creature combat'"
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block font-semibold text-sm mb-1">Commander Name</label>
              <input
                type="text"
                placeholder="e.g. Atraxa, Praetors' Voice"
                value={commanderName}
                onChange={(e) => setCommanderName(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block font-semibold text-sm mb-1">Ollama Model</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>

            <JankPreferences prefs={prefs} onChange={setPrefs} />

            <button
              onClick={handleRecommend}
              disabled={loading || !concept.trim() || !commanderName.trim()}
              className="w-full bg-indigo-600 text-white py-2 rounded font-semibold disabled:opacity-50"
            >
              {loading ? "Thinking..." : "Get Recommendations"}
            </button>

            {error && <p className="text-red-500 text-sm">{error}</p>}
          </div>

          {/* Right panel */}
          <div className="bg-white rounded-xl shadow p-6">
            {result ? (
              <RecommendationPanel text={result.text} contextCards={result.context} />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                Recommendations will appear here
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
