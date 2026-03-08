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
  ExternalLink
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
    <div className="w-full bg-white rounded-3xl shadow-xl border border-zinc-100 overflow-hidden relative flex flex-col md:flex-row text-left">
      <div className="absolute top-0 left-0 w-full h-1 bg-zinc-100 z-10">
        <motion.div
          className="h-full bg-indigo-500"
          initial={{ width: "0%" }}
          animate={{
            width: `${((currentStepIndex + 1) / STEPS.length) * 100}%`,
          }}
          transition={{ duration: 1.0, ease: "linear" }}
        />
      </div>

      {/* Main Timeline Panel */}
      <div className="flex-1 p-8 sm:p-12 border-b md:border-b-0 md:border-r border-zinc-100">
        <div className="mb-10">
          <div className="inline-flex items-center justify-center p-3 bg-indigo-50 text-indigo-600 rounded-2xl mb-6 shadow-sm ring-1 ring-indigo-100">
            <Sparkles className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-display font-medium text-zinc-900 mb-2">
            NovaPilot is working
          </h2>
          <p className="text-zinc-500 max-w-md truncate">
            &quot;{query}&quot;
          </p>
        </div>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[1.1875rem] top-6 bottom-6 w-px bg-zinc-200" />

          <div className="space-y-6">
            {STEPS.map((step, index) => {
              const isCompleted = index < currentStepIndex;
              const isCurrent = index === currentStepIndex;
              const isPending = index > currentStepIndex;
              const Icon = step.icon;

              return (
                <div key={step.id} className="relative flex items-start gap-6 group">
                  {/* Status Indicator / Icon */}
                  <div className="relative z-10 flex-shrink-0">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors duration-500 ${
                      isCompleted ? 'bg-emerald-50 border-emerald-200 text-emerald-600' :
                      isCurrent ? 'bg-indigo-50 border-indigo-500 text-indigo-600 shadow-[0_0_15px_rgba(99,102,241,0.2)]' :
                      'bg-white border-zinc-200 text-zinc-400'
                    }`}>
                      {isCompleted ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : isCurrent ? (
                        <Icon className="w-5 h-5 animate-pulse" />
                      ) : (
                        <Icon className="w-5 h-5" />
                      )}
                    </div>
                    
                    {/* Active ring animation */}
                    {isCurrent && (
                      <div className="absolute inset-0 rounded-full border border-indigo-500 animate-ping opacity-20" />
                    )}
                  </div>

                  {/* Content */}
                  <div className={`flex-1 pt-2 transition-all duration-500 ${
                    isPending ? 'opacity-40' : 'opacity-100'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <h3 className={`font-medium text-lg ${
                        isCompleted ? 'text-zinc-900' :
                        isCurrent ? 'text-indigo-600' :
                        'text-zinc-500'
                      }`}>
                        {step.label}
                      </h3>
                      {isCurrent && (
                        <span className="text-xs font-medium text-indigo-600 flex items-center gap-1.5 bg-indigo-50 px-2 py-0.5 rounded-full">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Processing
                        </span>
                      )}
                    </div>
                    
                    {/* Progress Bar for active step */}
                    <AnimatePresence>
                      {isCurrent && (
                        <motion.div 
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-3 overflow-hidden"
                        >
                          <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
                            <motion.div 
                              className="h-full bg-indigo-500 rounded-full"
                              initial={{ width: "0%" }}
                              animate={{ width: "100%" }}
                              transition={{ duration: 1.0, ease: "linear" }}
                            />
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
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
          <h3 className="font-medium text-zinc-900 flex items-center gap-2">
            <ShoppingCart className="w-4 h-4 text-zinc-500" />
            Live Extractions
          </h3>
          <span className="text-xs font-medium bg-zinc-200 text-zinc-600 px-2 py-1 rounded-md">
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
                className="h-40 flex flex-col items-center justify-center text-center py-8 px-4 border border-dashed border-zinc-300 rounded-xl"
              >
                <Search className="w-6 h-6 text-zinc-400 mb-2" />
                <p className="text-sm text-zinc-500">Waiting for agent to find products...</p>
              </motion.div>
            ) : (
              extractedProducts.map((product, idx) => (
                <motion.div
                  key={product.id}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ delay: idx * 0.1 }}
                  className="group bg-white border border-zinc-200 hover:border-zinc-300 shadow-sm rounded-xl p-3 flex gap-4 transition-colors"
                >
                  <div className="w-16 h-16 rounded-lg bg-zinc-100 overflow-hidden flex-shrink-0">
                    <img 
                      src={product.image} 
                      alt={product.name}
                      className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                    />
                  </div>
                  <div className="flex-1 min-w-0 py-0.5">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-medium text-sm text-zinc-900 truncate">{product.name}</h4>
                      <ExternalLink className="w-3.5 h-3.5 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                    </div>
                    <div className="text-indigo-600 font-semibold text-sm mb-1.5">{product.price}</div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded">{product.store}</span>
                      <span className="text-amber-500 flex items-center gap-0.5">
                        ★ {product.rating}
                      </span>
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
