import { Brain } from "lucide-react";

interface ReasoningPanelProps {
  reasoning: string;
}

export function ReasoningPanel({ reasoning }: ReasoningPanelProps) {
  return (
    <div className="bg-zinc-900 rounded-3xl p-8 relative overflow-hidden shadow-xl">
      <div className="absolute top-0 right-0 p-8 opacity-5">
        <Brain className="w-32 h-32 text-white" />
      </div>
      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-white/10 p-2 rounded-xl text-white backdrop-blur-sm">
            <Brain className="w-5 h-5" />
          </div>
          <h3 className="text-xl font-display font-bold text-white">
            AI Reasoning
          </h3>
        </div>
        <p className="text-base text-zinc-300 leading-relaxed max-w-3xl">
          {reasoning}
        </p>
      </div>
    </div>
  );
}
