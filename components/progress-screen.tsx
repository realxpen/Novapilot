"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  CheckCircle2,
  Loader2,
  Search,
  Brain,
  ShoppingCart,
  BarChart3,
  Sparkles,
} from "lucide-react";

interface ProgressScreenProps {
  query: string;
}

const STEPS = [
  { id: "understanding", label: "Understanding request", icon: Brain },
  { id: "jumia", label: "Searching Jumia", icon: ShoppingCart },
  { id: "amazon", label: "Searching Amazon", icon: Search },
  { id: "extracting", label: "Extracting product data", icon: BarChart3 },
  { id: "comparing", label: "Comparing results", icon: Sparkles },
];

export function ProgressScreen({ query }: ProgressScreenProps) {
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
    }, 1200); // 1.2s per step

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-white rounded-3xl shadow-xl border border-zinc-100 p-8 sm:p-12 overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full h-1 bg-zinc-100">
        <motion.div
          className="h-full bg-indigo-500"
          initial={{ width: "0%" }}
          animate={{
            width: `${((currentStepIndex + 1) / STEPS.length) * 100}%`,
          }}
          transition={{ duration: 1.2, ease: "linear" }}
        />
      </div>

      <div className="mb-10 text-center">
        <div className="inline-flex items-center justify-center p-3 bg-indigo-50 text-indigo-600 rounded-2xl mb-6 shadow-sm ring-1 ring-indigo-100">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-display font-medium text-zinc-900 mb-2">
          NovaPilot is working
        </h2>
        <p className="text-zinc-500 max-w-md mx-auto truncate">
          &quot;{query}&quot;
        </p>
      </div>

      <div className="space-y-6 max-w-md mx-auto">
        {STEPS.map((step, index) => {
          const isCompleted = index < currentStepIndex;
          const isCurrent = index === currentStepIndex;
          const isPending = index > currentStepIndex;
          const Icon = step.icon;

          return (
            <div
              key={step.id}
              className={`flex items-center gap-4 transition-all duration-500 ${
                isPending ? "opacity-40" : "opacity-100"
              }`}
            >
              <div
                className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors duration-300 ${
                  isCompleted
                    ? "bg-emerald-100 text-emerald-600"
                    : isCurrent
                      ? "bg-indigo-100 text-indigo-600"
                      : "bg-zinc-100 text-zinc-400"
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>

              <div className="flex-1">
                <p
                  className={`text-base font-medium transition-colors duration-300 ${
                    isCompleted
                      ? "text-zinc-900"
                      : isCurrent
                        ? "text-indigo-600"
                        : "text-zinc-500"
                  }`}
                >
                  {step.label}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
