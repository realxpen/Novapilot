"use client";

import { useState } from "react";
import { SearchInput } from "./search-input";
import { ExamplePromptList } from "./example-prompt-list";

interface HomeSearchProps {
  onSearch: (query: string) => void;
}

const SUGGESTIONS = [
  "Compare the best phones under ₦500,000",
  "Find the best laptop for programming under ₦900,000",
  "Compare 3 tablets for graphic design",
];

export function HomeSearch({ onSearch }: HomeSearchProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <div className="flex flex-col items-center w-full">
      <div className="mb-10 flex flex-col items-center text-center">
        <h1 className="text-4xl sm:text-6xl font-display font-bold tracking-tight text-zinc-900 mb-6">
          What are you looking for?
        </h1>
        <p className="text-lg text-zinc-500 max-w-xl">
          Describe what you need, and NovaPilot will search, compare, and recommend the best options across the web.
        </p>
      </div>

      <SearchInput query={query} setQuery={setQuery} onSubmit={handleSubmit} />
      <ExamplePromptList suggestions={SUGGESTIONS} onSelect={setQuery} />
    </div>
  );
}
