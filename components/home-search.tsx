"use client";

import { useState } from "react";
import { SearchInput } from "./search-input";
import { ExamplePromptList } from "./example-prompt-list";

interface HomeSearchProps {
  onSearch: (query: string) => void;
}

const SUGGESTIONS = [
  "Best phones under ₦500k",
  "Laptop for programming under ₦900k",
  "Tablets for graphic design",
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
      <div className="mb-8 flex flex-col items-center text-center">
        <h1 className="text-3xl sm:text-4xl font-sans font-semibold tracking-tight text-zinc-900 mb-4">
          Where knowledge begins
        </h1>
      </div>

      <SearchInput query={query} setQuery={setQuery} onSubmit={handleSubmit} />
      <ExamplePromptList suggestions={SUGGESTIONS} onSelect={setQuery} />
    </div>
  );
}
