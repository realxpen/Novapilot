interface ExamplePromptListProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
}

export function ExamplePromptList({ suggestions, onSelect }: ExamplePromptListProps) {
  return (
    <div className="mt-10 w-full">
      <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-4 text-center">
        Try these examples
      </p>
      <div className="flex flex-wrap gap-2 justify-center">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSelect(suggestion)}
            className="px-4 py-2 bg-white border border-zinc-200 rounded-full text-sm text-zinc-600 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition-all shadow-sm"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
