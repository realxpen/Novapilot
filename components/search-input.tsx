import { Search, ArrowRight } from "lucide-react";

interface SearchInputProps {
  query: string;
  setQuery: (query: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function SearchInput({ query, setQuery, onSubmit }: SearchInputProps) {
  return (
    <form onSubmit={onSubmit} className="w-full relative group max-w-3xl mx-auto">
      <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-3xl sm:rounded-full blur-xl transition-opacity opacity-0 group-hover:opacity-100 duration-500" />
      <div className="relative flex flex-col sm:flex-row items-center bg-white rounded-3xl sm:rounded-full shadow-lg shadow-zinc-200/50 ring-1 ring-zinc-200 focus-within:ring-2 focus-within:ring-indigo-500 transition-all p-2 w-full">
        <div className="pl-6 pr-2 text-zinc-400 hidden sm:block">
          <Search className="w-6 h-6" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Find the best laptop under ₦800,000 for UI/UX design"
          className="w-full py-4 px-4 sm:px-2 bg-transparent border-none focus:outline-none text-lg text-zinc-900 placeholder:text-zinc-400 h-16 sm:h-auto"
        />
        <button
          type="submit"
          disabled={!query.trim()}
          className="w-full sm:w-auto mt-2 sm:mt-0 bg-indigo-600 text-white px-8 py-4 rounded-2xl sm:rounded-full font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 whitespace-nowrap shadow-md shadow-indigo-200"
        >
          Run NovaPilot
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </form>
  );
}
