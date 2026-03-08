import { Sparkles } from "lucide-react";

interface ReasoningPanelProps {
  reasoning: string;
}

export function ReasoningPanel({ reasoning }: ReasoningPanelProps) {
  return (
    <div className="bg-white rounded-xl p-6 md:p-8 border border-zinc-200 shadow-sm relative">
      <div className="flex items-start gap-4">
        <div className="bg-zinc-100 p-2 rounded-lg text-zinc-900 flex-shrink-0 mt-1">
          <Sparkles className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-zinc-900 mb-2">
            AI Reasoning
          </h3>
          <p className="text-sm text-zinc-700 leading-relaxed max-w-3xl">
            {reasoning}
          </p>
        </div>
      </div>
    </div>
  );
}
