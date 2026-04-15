import type { JankPreferences } from "../api/client";

interface Props {
  prefs: JankPreferences;
  onChange: (prefs: JankPreferences) => void;
}

const OPTIONS: { key: keyof JankPreferences; label: string; description: string }[] = [
  {
    key: "synergy_first",
    label: "Synergy-First",
    description: "Find mechanical synergies from oracle text. Ignores card popularity entirely.",
  },
  {
    key: "hidden_gems",
    label: "Hidden Gems",
    description: "Surface underplayed cards most players overlook but that synergize well.",
  },
  {
    key: "chaos_injection",
    label: "Chaos Injection",
    description: "Deliberately include off-meta, jank, or meme-worthy cards that still advance the theme.",
  },
  {
    key: "llm_choice",
    label: "LLM's Choice",
    description: "Let the AI blend all of the above based on what makes the deck most interesting.",
  },
];

export function JankPreferences({ prefs, onChange }: Props) {
  const toggle = (key: keyof JankPreferences) => {
    onChange({ ...prefs, [key]: !prefs[key] });
  };

  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-sm text-gray-700 uppercase tracking-wide">
        Recommendation Style
      </h3>
      {OPTIONS.map(({ key, label, description }) => (
        <label key={key} className="flex items-start gap-3 cursor-pointer group">
          <input
            type="checkbox"
            checked={prefs[key]}
            onChange={() => toggle(key)}
            className="mt-1 accent-indigo-600"
          />
          <div>
            <span className="font-medium text-sm">{label}</span>
            <p className="text-xs text-gray-500">{description}</p>
          </div>
        </label>
      ))}
    </div>
  );
}
