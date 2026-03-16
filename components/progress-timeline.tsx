"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  CheckCircle2,
  Loader2,
  Search,
  Brain,
  ShoppingCart,
  FileText,
  GitCompare,
  Sparkles,
  Circle
} from "lucide-react";

interface ProgressTimelineProps {
  query: string;
}

const STEPS = [
  { id: "understanding", label: "Understanding request", icon: Brain },
  { id: "jumia", label: "Searching Jumia", icon: ShoppingCart },
  { id: "shopinverse", label: "Searching ShopInverse", icon: Search },
  { id: "extracting", label: "Extracting product details", icon: FileText },
  { id: "comparing", label: "Comparing results", icon: GitCompare },
  { id: "generating", label: "Generating recommendation", icon: Sparkles },
];

export function ProgressTimeline({ query }: ProgressTimelineProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev < STEPS.length - 1) {
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 1000); // 1s per step

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-white rounded-2xl shadow-sm border border-zinc-200 overflow-hidden relative flex flex-col md:flex-row text-left">
      {/* Main Timeline Panel */}
      <div className="flex-1 p-8 sm:p-10 border-b md:border-b-0 md:border-r border-zinc-100">
        <div className="mb-8">
          <h2 className="text-xl font-sans font-semibold text-zinc-900 mb-2 flex items-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
            Researching
          </h2>
          <p className="text-zinc-500 text-sm max-w-md truncate">
            &quot;{query}&quot;
          </p>
        </div>

        <div className="relative">
          <div className="space-y-4">
            {STEPS.map((step, index) => {
              const isCompleted = index < currentStepIndex;
              const isCurrent = index === currentStepIndex;
              const isPending = index > currentStepIndex;

              return (
                <div key={step.id} className="relative flex items-center gap-4 group">
                  {/* Status Indicator / Icon */}
                  <div className="relative z-10 flex-shrink-0">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors duration-500 ${
                      isCompleted ? 'text-zinc-900' :
                      isCurrent ? 'text-zinc-900' :
                      'text-zinc-300'
                    }`}>
                      {isCompleted ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : isCurrent ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Circle className="w-4 h-4" />
                      )}
                    </div>
                  </div>

                  {/* Content */}
                  <div className={`flex-1 transition-all duration-500 ${
                    isPending ? 'opacity-40' : 'opacity-100'
                  }`}>
                    <h3 className={`font-medium text-sm ${
                      isCompleted ? 'text-zinc-900' :
                      isCurrent ? 'text-zinc-900' :
                      'text-zinc-500'
                    }`}>
                      {step.label}
                    </h3>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-full md:w-80 bg-zinc-50/50 p-6 sm:p-8 flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-sm font-medium text-zinc-900 flex items-center gap-2">
            <ShoppingCart className="w-4 h-4 text-zinc-500" />
            Live Extractions
          </h3>
          <span className="text-xs font-medium bg-zinc-200/50 text-zinc-600 px-2 py-1 rounded-md">
            live data pending
          </span>
        </div>

        <div className="flex-1">
          <AnimatePresence>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-32 flex flex-col items-center justify-center text-center py-8 px-4 border border-dashed border-zinc-200 rounded-xl"
            >
              <Search className="w-5 h-5 text-zinc-300 mb-2" />
              <p className="text-xs text-zinc-500">Waiting for live product extraction...</p>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
