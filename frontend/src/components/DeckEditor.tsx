import { useState } from "react";
import { importArchidektDeck } from "../api/client";
import type { DeckCard } from "../api/client";

interface Props {
  cards: DeckCard[];
  onCardsChange: (cards: DeckCard[]) => void;
}

export function DeckEditor({ cards, onCardsChange }: Props) {
  const [urlInput, setUrlInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deckName, setDeckName] = useState("");

  const handleImport = async () => {
    setLoading(true);
    setError(null);
    try {
      const deck = await importArchidektDeck(urlInput);
      setDeckName(deck.name);
      onCardsChange(deck.cards);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold">Deck</h2>
        {deckName && <p className="text-sm text-gray-500">{deckName}</p>}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Archidekt deck URL or ID"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button
          onClick={handleImport}
          disabled={loading || !urlInput}
          className="bg-indigo-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
        >
          {loading ? "Importing..." : "Import"}
        </button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {cards.length > 0 && (
        <div className="max-h-64 overflow-y-auto border rounded p-2 space-y-1">
          {cards.map((card, i) => (
            <div key={i} className="flex justify-between text-sm">
              <span>{card.name}</span>
              <span className="text-gray-400">x{card.quantity}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
