"use client";

import { ArrowLeft } from "lucide-react";
import { RecommendationCard } from "./recommendation-card";
import { ProductCard } from "./product-card";
import { ComparisonTable } from "./comparison-table";
import { ReasoningPanel } from "./reasoning-panel";

interface ResultsDashboardProps {
  query: string;
  onReset: () => void;
}

const BEST_RECOMMENDATION = {
  name: 'Dell XPS 13 (2024)',
  price: "₦785,000",
  store: "Amazon",
  rating: 4.8,
  score: 98,
  image: "https://picsum.photos/seed/dellxps/800/600",
  specs: {
    cpu: "Intel Core Ultra 7",
    ram: "16GB LPDDR5x",
    storage: "512GB PCIe SSD",
    display: '13.4" FHD+ InfinityEdge',
    battery: "Up to 14 hours",
  },
  reason: "Offers the best balance of performance, RAM, and price for UI/UX design workloads while remaining within the ₦800,000 budget.",
};

const ALTERNATIVES = [
  {
    id: 1,
    name: "MacBook Air M2 (13-inch)",
    price: "₦795,000",
    store: "Jumia",
    rating: 4.9,
    score: 95,
    image: "https://picsum.photos/seed/macbookair/400/300",
    keySpec: "Apple M2, 8GB RAM, 256GB SSD",
  },
  {
    id: 2,
    name: "ASUS Zenbook 14 OLED",
    price: "₦720,000",
    store: "Konga",
    rating: 4.6,
    score: 92,
    image: "https://picsum.photos/seed/zenbook/400/300",
    keySpec: "Ryzen 7, 16GB RAM, 512GB SSD",
  },
];

const COMPARISON_DATA = [
  {
    product: "Dell XPS 13 (2024)",
    price: "₦785,000",
    ram: "16GB",
    storage: "512GB",
    cpu: "Core Ultra 7",
    rating: "4.8",
    score: "98/100",
    isBest: true,
  },
  {
    product: "MacBook Air M2",
    price: "₦795,000",
    ram: "8GB",
    storage: "256GB",
    cpu: "Apple M2",
    rating: "4.9",
    score: "95/100",
    isBest: false,
  },
  {
    product: "ASUS Zenbook 14",
    price: "₦720,000",
    ram: "16GB",
    storage: "512GB",
    cpu: "Ryzen 7",
    rating: "4.6",
    score: "92/100",
    isBest: false,
  },
];

const REASONING_TEXT = "NovaPilot recommends the Dell XPS 13 because it offers the best balance of performance, RAM, and price for UI/UX design workloads while remaining within the ₦800,000 budget. The Intel Core Ultra 7 processor combined with 16GB of LPDDR5x RAM ensures smooth multitasking across Figma, Adobe Creative Cloud, and multiple browser tabs. While the MacBook Air M2 is a strong contender, its base 8GB RAM configuration may bottleneck heavy design files, making the XPS 13 the more future-proof choice at this price point.";

export function ResultsDashboard({ query, onReset }: ResultsDashboardProps) {
  return (
    <div className="w-full pb-20 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onReset}
          className="flex items-center gap-2 text-sm font-medium text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Search
        </button>
        <div className="text-sm text-zinc-600 truncate max-w-md bg-zinc-100/80 px-3 py-1.5 rounded-md border border-zinc-200/50 flex items-center gap-2">
          <span className="font-semibold text-zinc-900">Query:</span>
          <span className="truncate">&quot;{query}&quot;</span>
        </div>
      </div>

      <div className="space-y-8">
        {/* Top Section: Best Recommendation Card */}
        <section>
          <RecommendationCard recommendation={BEST_RECOMMENDATION} />
        </section>

        {/* Second Section: Alternative Options */}
        <section>
          <h3 className="text-lg font-sans font-semibold text-zinc-900 mb-4 flex items-center gap-2">
            Alternative Options
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ALTERNATIVES.map((alt) => (
              <ProductCard key={alt.id} product={alt} />
            ))}
          </div>
        </section>

        {/* Third Section: Comparison Table */}
        <section>
          <h3 className="text-lg font-sans font-semibold text-zinc-900 mb-4">
            Comparison Table
          </h3>
          <ComparisonTable data={COMPARISON_DATA} />
        </section>

        {/* Fourth Section: AI Reasoning Panel */}
        <section>
          <ReasoningPanel reasoning={REASONING_TEXT} />
        </section>
      </div>
    </div>
  );
}
