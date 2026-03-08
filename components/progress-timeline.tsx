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
  ExternalLink,
  Circle
} from "lucide-react";

interface ProgressTimelineProps {
  query: string;
}

const STEPS = [
  { id: "understanding", label: "Understanding request", icon: Brain },
  { id: "jumia", label: "Searching Jumia", icon: ShoppingCart },
  { id: "amazon", label: "Searching Amazon", icon: Search },
  { id: "extracting", label: "Extracting product details", icon: FileText },
  { id: "comparing", label: "Comparing results", icon: GitCompare },
  { id: "generating", label: "Generating recommendation", icon: Sparkles },
];

const MOCK_PRODUCTS = [
  {
    id: 'p1',
    name: 'Sony WH-CH720N',
    price: '$148.00',
    store: 'Amazon',
    rating: '4.6',
    image: 'https://picsum.photos/seed/sony/200/200'
  },
  {
    id: 'p2',
    name: 'Soundcore Space Q45',
    price: '$149.99',
    store: 'Jumia',
    rating: '4.5',
    image: 'https://picsum.photos/seed/soundcore/200/200'
  },
  {
    id: 'p3',
    name: 'Sennheiser HD 450BT',
    price: '$129.95',
    store: 'Amazon',
    rating: '4.3',
    image: 'https://picsum.photos/seed/sennheiser/200/200'
  }
];

export function ProgressTimeline({ query }: ProgressTimelineProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [extractedProducts, setExtractedProducts] = useState<typeof MOCK_PRODUCTS>([]);

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

  useEffect(() => {
    if (currentStepIndex === 3) {
      setExtractedProducts([MOCK_PRODUCTS[0]]);
    } else if (currentStepIndex === 4) {
      setExtractedProducts([MOCK_PRODUCTS[0], MOCK_PRODUCTS[1]]);
    } else if (currentStepIndex === 5) {
      setExtractedProducts(MOCK_PRODUCTS);
    }
  }, [currentStepIndex]);

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
            {extractedProducts.length} items
          </span>
        </div>

        <div className="flex-1 space-y-3">
          <AnimatePresence>
            {extractedProducts.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-32 flex flex-col items-center justify-center text-center py-8 px-4 border border-dashed border-zinc-200 rounded-xl"
              >
                <Search className="w-5 h-5 text-zinc-300 mb-2" />
                <p className="text-xs text-zinc-500">Waiting for agent to find products...</p>
              </motion.div>
            ) : (
              extractedProducts.map((product, idx) => (
                <motion.div
                  key={product.id}
                  initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ delay: idx * 0.1 }}
                  className="group bg-white border border-zinc-200 hover:border-zinc-300 shadow-sm rounded-xl p-2.5 flex gap-3 transition-colors"
                >
                  <div className="w-12 h-12 rounded-lg bg-zinc-100 overflow-hidden flex-shrink-0">
                    <img 
                      src={product.image} 
                      alt={product.name}
                      className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                    />
                  </div>
                  <div className="flex-1 min-w-0 py-0.5 flex flex-col justify-center">
                    <div className="flex items-start justify-between gap-2 mb-0.5">
                      <h4 className="font-medium text-xs text-zinc-900 truncate">{product.name}</h4>
                    </div>
                    <div className="text-zinc-900 font-semibold text-xs mb-1">{product.price}</div>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-zinc-500">{product.store}</span>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
