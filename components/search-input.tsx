import { ArrowRight, Paperclip, Globe } from "lucide-react";

interface SearchInputProps {
  query: string;
  setQuery: (query: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function SearchInput({ query, setQuery, onSubmit }: SearchInputProps) {
  return (
    <form onSubmit={onSubmit} className="w-full relative max-w-3xl mx-auto">
      <div className="relative flex flex-col bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] ring-1 ring-zinc-200/80 focus-within:ring-2 focus-within:ring-zinc-900 transition-all w-full overflow-hidden">
        <textarea
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything..."
          rows={1}
          className="w-full py-4 px-5 bg-transparent border-none focus:outline-none text-lg text-zinc-900 placeholder:text-zinc-400 resize-none min-h-[60px]"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (query.trim()) onSubmit(e);
            }
          }}
        />
        <div className="flex items-center justify-between px-3 pb-3 pt-1">
          <div className="flex items-center gap-2 text-zinc-400">
            <button type="button" className="p-2 hover:bg-zinc-100 rounded-lg transition-colors flex items-center gap-1.5 text-xs font-medium">
              <Globe className="w-4 h-4" />
              <span>Focus</span>
            </button>
            <button type="button" className="p-2 hover:bg-zinc-100 rounded-lg transition-colors flex items-center gap-1.5 text-xs font-medium">
              <Paperclip className="w-4 h-4" />
              <span>Attach</span>
            </button>
          </div>
          <button
            type="submit"
            disabled={!query.trim()}
            className="bg-zinc-900 text-white p-2 rounded-xl hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </form>
  );
}
