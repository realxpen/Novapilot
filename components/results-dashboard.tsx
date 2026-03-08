"use client";

import { motion } from "motion/react";
import {
  ArrowLeft,
  ExternalLink,
  Star,
  CheckCircle2,
  AlertCircle,
  ShoppingCart,
  Cpu,
  Battery,
  Monitor,
  HardDrive,
  Sparkles,
  Brain,
} from "lucide-react";
import Image from "next/image";

interface ResultsDashboardProps {
  query: string;
  onReset: () => void;
}

const BEST_RECOMMENDATION = {
  name: 'MacBook Pro 14" (M3 Pro, 2023)',
  price: "₦785,000",
  store: "Amazon",
  rating: 4.9,
  reviews: 1240,
  image: "https://picsum.photos/seed/macbook/800/600",
  specs: {
    cpu: "Apple M3 Pro (11-core)",
    ram: "18GB Unified Memory",
    storage: "512GB SSD",
    display: '14.2" Liquid Retina XDR',
    battery: "Up to 18 hours",
  },
  pros: [
    "Incredible performance for UI/UX tools (Figma, Adobe CC)",
    "Industry-leading display accuracy",
    "Exceptional battery life",
    "Fits within the ₦800k budget",
  ],
  cons: ["Limited ports compared to older models", "Expensive upgrades"],
};

const ALTERNATIVES = [
  {
    id: 1,
    name: "Dell XPS 15 (2023)",
    price: "₦750,000",
    store: "Jumia",
    rating: 4.7,
    image: "https://picsum.photos/seed/dell/400/300",
    keySpec: "Intel Core i7, 16GB RAM, OLED",
  },
  {
    id: 2,
    name: "ASUS ROG Zephyrus G14",
    price: "₦680,000",
    store: "Konga",
    rating: 4.6,
    image: "https://picsum.photos/seed/asus/400/300",
    keySpec: "Ryzen 9, 16GB RAM, 120Hz",
  },
];

export function ResultsDashboard({ query, onReset }: ResultsDashboardProps) {
  return (
    <div className="w-full pb-20">
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onReset}
          className="flex items-center gap-2 text-sm font-medium text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Search
        </button>
        <div className="text-sm text-zinc-500 truncate max-w-md bg-white px-4 py-2 rounded-full shadow-sm border border-zinc-100">
          <span className="font-medium text-zinc-900">Query:</span> &quot;
          {query}&quot;
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Recommendation Column */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white rounded-3xl shadow-xl border border-zinc-100 overflow-hidden relative group">
            <div className="absolute top-4 left-4 z-10 bg-indigo-600 text-white text-xs font-bold uppercase tracking-wider py-1.5 px-3 rounded-full shadow-md flex items-center gap-1.5">
              <Star className="w-3.5 h-3.5 fill-current" />
              Best Recommendation
            </div>

            <div className="relative h-72 w-full bg-zinc-100">
              <Image
                src={BEST_RECOMMENDATION.image}
                alt={BEST_RECOMMENDATION.name}
                fill
                className="object-cover"
                referrerPolicy="no-referrer"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <div className="absolute bottom-6 left-6 right-6 flex justify-between items-end">
                <div>
                  <h2 className="text-3xl font-display font-bold text-white mb-2">
                    {BEST_RECOMMENDATION.name}
                  </h2>
                  <div className="flex items-center gap-3 text-white/90 text-sm">
                    <span className="flex items-center gap-1 bg-white/20 backdrop-blur-md px-2.5 py-1 rounded-md">
                      <ShoppingCart className="w-4 h-4" />
                      {BEST_RECOMMENDATION.store}
                    </span>
                    <span className="flex items-center gap-1 bg-white/20 backdrop-blur-md px-2.5 py-1 rounded-md">
                      <Star className="w-4 h-4 fill-current text-yellow-400" />
                      {BEST_RECOMMENDATION.rating} (
                      {BEST_RECOMMENDATION.reviews})
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-white">
                    {BEST_RECOMMENDATION.price}
                  </div>
                </div>
              </div>
            </div>

            <div className="p-8">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                <div className="flex flex-col gap-1 p-4 rounded-2xl bg-zinc-50 border border-zinc-100">
                  <Cpu className="w-5 h-5 text-indigo-500 mb-1" />
                  <span className="text-xs text-zinc-500 font-medium">
                    Processor
                  </span>
                  <span className="text-sm font-semibold text-zinc-900 truncate">
                    {BEST_RECOMMENDATION.specs.cpu}
                  </span>
                </div>
                <div className="flex flex-col gap-1 p-4 rounded-2xl bg-zinc-50 border border-zinc-100">
                  <HardDrive className="w-5 h-5 text-indigo-500 mb-1" />
                  <span className="text-xs text-zinc-500 font-medium">
                    Memory & Storage
                  </span>
                  <span className="text-sm font-semibold text-zinc-900 truncate">
                    {BEST_RECOMMENDATION.specs.ram}
                  </span>
                </div>
                <div className="flex flex-col gap-1 p-4 rounded-2xl bg-zinc-50 border border-zinc-100">
                  <Monitor className="w-5 h-5 text-indigo-500 mb-1" />
                  <span className="text-xs text-zinc-500 font-medium">
                    Display
                  </span>
                  <span className="text-sm font-semibold text-zinc-900 truncate">
                    {BEST_RECOMMENDATION.specs.display}
                  </span>
                </div>
                <div className="flex flex-col gap-1 p-4 rounded-2xl bg-zinc-50 border border-zinc-100">
                  <Battery className="w-5 h-5 text-indigo-500 mb-1" />
                  <span className="text-xs text-zinc-500 font-medium">
                    Battery
                  </span>
                  <span className="text-sm font-semibold text-zinc-900 truncate">
                    {BEST_RECOMMENDATION.specs.battery}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 mb-8">
                <div>
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    Why it&apos;s great
                  </h3>
                  <ul className="space-y-3">
                    {BEST_RECOMMENDATION.pros.map((pro, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-zinc-600"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                        {pro}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-500" />
                    Things to consider
                  </h3>
                  <ul className="space-y-3">
                    {BEST_RECOMMENDATION.cons.map((con, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-zinc-600"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
                        {con}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <button className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-colors flex items-center justify-center gap-2 shadow-md shadow-indigo-200">
                View on {BEST_RECOMMENDATION.store}
                <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Comparison Table */}
          <div className="bg-white rounded-3xl shadow-sm border border-zinc-200 p-8">
            <h3 className="text-lg font-display font-bold text-zinc-900 mb-6">
              Spec Comparison
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-zinc-500 uppercase bg-zinc-50 rounded-t-xl">
                  <tr>
                    <th className="px-6 py-4 font-medium rounded-tl-xl">
                      Feature
                    </th>
                    <th className="px-6 py-4 font-medium text-indigo-600">
                      MacBook Pro 14&quot;
                    </th>
                    <th className="px-6 py-4 font-medium">Dell XPS 15</th>
                    <th className="px-6 py-4 font-medium rounded-tr-xl">
                      ASUS ROG G14
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-6 py-4 font-medium text-zinc-900">
                      Processor
                    </td>
                    <td className="px-6 py-4 text-zinc-600">
                      M3 Pro (11-core)
                    </td>
                    <td className="px-6 py-4 text-zinc-600">Core i7-13700H</td>
                    <td className="px-6 py-4 text-zinc-600">Ryzen 9 7940HS</td>
                  </tr>
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-6 py-4 font-medium text-zinc-900">
                      Display
                    </td>
                    <td className="px-6 py-4 text-zinc-600">
                      14.2&quot; Mini-LED 120Hz
                    </td>
                    <td className="px-6 py-4 text-zinc-600">
                      15.6&quot; OLED 60Hz
                    </td>
                    <td className="px-6 py-4 text-zinc-600">
                      14&quot; IPS 165Hz
                    </td>
                  </tr>
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-6 py-4 font-medium text-zinc-900">
                      Battery Life
                    </td>
                    <td className="px-6 py-4 text-zinc-600">~18 hours</td>
                    <td className="px-6 py-4 text-zinc-600">~8 hours</td>
                    <td className="px-6 py-4 text-zinc-600">~10 hours</td>
                  </tr>
                  <tr className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-6 py-4 font-medium text-zinc-900">
                      Weight
                    </td>
                    <td className="px-6 py-4 text-zinc-600">1.61 kg</td>
                    <td className="px-6 py-4 text-zinc-600">1.92 kg</td>
                    <td className="px-6 py-4 text-zinc-600">1.65 kg</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-8">
          {/* AI Reasoning Panel */}
          <div className="bg-indigo-50 rounded-3xl p-6 border border-indigo-100 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Sparkles className="w-24 h-24 text-indigo-600" />
            </div>
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-indigo-600 p-1.5 rounded-lg text-white">
                  <Brain className="w-4 h-4" />
                </div>
                <h3 className="font-display font-bold text-indigo-900">
                  NovaPilot Reasoning
                </h3>
              </div>
              <p className="text-sm text-indigo-800/80 leading-relaxed mb-4">
                Based on your requirement for &quot;UI/UX design&quot; under
                &quot;₦800,000&quot;, the MacBook Pro 14&quot; with M3 Pro is
                the optimal choice.
              </p>
              <p className="text-sm text-indigo-800/80 leading-relaxed">
                UI/UX workflows heavily rely on single-core performance and
                memory bandwidth (crucial for Figma and Adobe CC). The Liquid
                Retina XDR display offers industry-leading color accuracy out of
                the box, which is essential for design work. While the Dell XPS
                15 offers an OLED screen, the MacBook&apos;s battery life and
                sustained performance on battery make it superior for
                professional use.
              </p>
            </div>
          </div>

          {/* Alternatives */}
          <div>
            <h3 className="text-lg font-display font-bold text-zinc-900 mb-4">
              Alternative Options
            </h3>
            <div className="space-y-4">
              {ALTERNATIVES.map((alt) => (
                <div
                  key={alt.id}
                  className="bg-white rounded-2xl p-4 shadow-sm border border-zinc-200 hover:border-indigo-300 transition-colors cursor-pointer group"
                >
                  <div className="flex gap-4">
                    <div className="relative w-20 h-20 rounded-xl overflow-hidden bg-zinc-100 flex-shrink-0">
                      <Image
                        src={alt.image}
                        alt={alt.name}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-500"
                        referrerPolicy="no-referrer"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-bold text-zinc-900 text-sm truncate mb-1">
                        {alt.name}
                      </h4>
                      <div className="text-indigo-600 font-semibold text-sm mb-1">
                        {alt.price}
                      </div>
                      <div className="text-xs text-zinc-500 truncate mb-2">
                        {alt.keySpec}
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-zinc-500 bg-zinc-100 px-2 py-0.5 rounded-md">
                          {alt.store}
                        </span>
                        <span className="flex items-center gap-1 text-xs font-medium text-zinc-600">
                          <Star className="w-3 h-3 fill-current text-yellow-400" />
                          {alt.rating}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
