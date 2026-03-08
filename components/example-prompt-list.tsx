interface ExamplePromptListProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
}

export function ExamplePromptList({ suggestions, onSelect }: ExamplePromptListProps) {
  return (
    <div className="mt-8 w-full">
      <div className="flex flex-wrap gap-2 justify-center">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSelect(suggestion)}
            className="px-3 py-1.5 bg-zinc-100/80 hover:bg-zinc-200/80 border border-transparent rounded-full text-xs font-medium text-zinc-600 hover:text-zinc-900 transition-all flex items-center gap-1.5"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
