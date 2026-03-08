"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Search, Sparkles, ArrowRight } from "lucide-react";

interface HomeSearchProps {
  onSearch: (query: string) => void;
}

const SUGGESTIONS = [
  "Find the best laptop under ₦800,000 for UI/UX design",
  "Compare noise-cancelling headphones under $200",
  "Best ergonomic office chair for back pain",
  "Top-rated 4K monitors for video editing",
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
      <div className="mb-12 flex flex-col items-center text-center">
        <div className="inline-flex items-center justify-center p-3 bg-indigo-50 text-indigo-600 rounded-2xl mb-6 shadow-sm ring-1 ring-indigo-100">
          <Sparkles className="w-8 h-8" />
        </div>
        <h1 className="text-4xl sm:text-5xl font-display font-medium tracking-tight text-zinc-900 mb-4">
          NovaPilot
        </h1>
        <p className="text-lg text-zinc-500 max-w-lg">
          Your AI shopping assistant. Describe what you need, and we&apos;ll
          find the best options across the web.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full relative group">
        <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-2xl blur-xl transition-opacity opacity-0 group-hover:opacity-100 duration-500" />
        <div className="relative flex items-center bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200 focus-within:ring-2 focus-within:ring-indigo-500 transition-all overflow-hidden">
          <div className="pl-6 pr-2 text-zinc-400">
            <Search className="w-6 h-6" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find the best laptop under ₦800,000 for UI/UX design"
            className="w-full py-5 px-2 bg-transparent border-none focus:outline-none text-lg text-zinc-900 placeholder:text-zinc-400"
          />
          <div className="pr-3 pl-2">
            <button
              type="submit"
              disabled={!query.trim()}
              className="bg-zinc-900 text-white p-3 rounded-xl hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            >
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </form>

      <div className="mt-10 w-full">
        <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-4 text-center">
          Try these examples
        </p>
        <div className="flex flex-wrap gap-2 justify-center">
          {SUGGESTIONS.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => setQuery(suggestion)}
              className="px-4 py-2 bg-white border border-zinc-200 rounded-full text-sm text-zinc-600 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition-all shadow-sm"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
