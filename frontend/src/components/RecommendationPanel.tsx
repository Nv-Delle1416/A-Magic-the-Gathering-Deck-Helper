interface Props {
  text: string;
  contextCards: string[];
}

export function RecommendationPanel({ text, contextCards }: Props) {
  if (!text) return null;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold">Recommendations</h2>
      <pre className="whitespace-pre-wrap text-sm bg-gray-50 border rounded p-4 leading-relaxed">
        {text}
      </pre>
      {contextCards.length > 0 && (
        <details className="text-xs text-gray-400">
          <summary className="cursor-pointer">
            Cards used as context ({contextCards.length})
          </summary>
          <ul className="mt-1 space-y-0.5">
            {contextCards.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
