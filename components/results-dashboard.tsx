"use client";

import { ArrowLeft, AlertTriangle } from "lucide-react";
import { RecommendationCard } from "./recommendation-card";
import { ProductCard } from "./product-card";
import { ComparisonTable } from "./comparison-table";
import { ReasoningPanel } from "./reasoning-panel";

export interface Product {
  name: string;
  store: string;
  price: number;
  currency: string;
  rating?: number | null;
  ram_gb?: number | null;
  storage_gb?: number | null;
  cpu?: string | null;
  gpu?: string | null;
  screen_size?: string | null;
  url?: string | null;
  score?: number | null;
  image_url?: string | null;
  short_reason?: string | null;
}

export interface NovaPilotResponse {
  status: string;
  query: string;
  interpreted_request: {
    category: string;
    budget_currency: string;
    budget_max?: number | null;
    use_case: string;
    priority_specs: string[];
    top_n: number;
  };
  execution_log: Array<{
    step_id: string;
    label: string;
    status: string;
    timestamp: string;
    details?: Record<string, unknown> | null;
  }>;
  best_pick?: Product | null;
  alternatives: Product[];
  comparison_table: Product[];
  reasoning: string;
  warnings?: string[] | null;
}

interface ResultsDashboardProps {
  query: string;
  onReset: () => void;
  result: NovaPilotResponse | null;
  error: string | null;
}

function formatPrice(price: number, currency: string): string {
  const locale = currency.toUpperCase() === "NGN" ? "en-NG" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: currency.toUpperCase(),
    maximumFractionDigits: 0,
  }).format(price);
}

function fallbackImage(product: Product): string {
  const label = encodeURIComponent(`${product.name}`.slice(0, 48));
  return `https://placehold.co/800x600/f4f4f5/27272a?text=${label}`;
}

export function ResultsDashboard({ query, onReset, result, error }: ResultsDashboardProps) {
  const bestPick = result?.best_pick ?? null;
  const alternatives = result?.alternatives ?? [];
  const comparison = result?.comparison_table ?? [];

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

      {error && (
        <div className="mb-6 bg-amber-50 text-amber-900 border border-amber-200 rounded-lg p-4 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {result?.warnings && result.warnings.length > 0 && (
        <div className="mb-6 bg-amber-50 text-amber-900 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 mt-0.5" />
            <div className="space-y-1">
              {result.warnings.map((warning) => (
                <p key={warning} className="text-sm">
                  {warning}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {!result && !error && (
        <div className="bg-white rounded-xl p-6 border border-zinc-200 text-sm text-zinc-600">
          No result available yet. Submit a query to fetch recommendations.
        </div>
      )}

      {result && (
        <div className="space-y-8">
          {bestPick && (
            <section>
              <RecommendationCard
                recommendation={{
                  name: bestPick.name,
                  price: formatPrice(bestPick.price, bestPick.currency),
                  store: bestPick.store,
                  rating: bestPick.rating ?? 0,
                  score: bestPick.score ?? 0,
                  image: bestPick.image_url || fallbackImage(bestPick),
                  specs: {
                    cpu: bestPick.cpu || "Not specified",
                    ram: bestPick.ram_gb ? `${bestPick.ram_gb}GB` : "Not specified",
                    storage: bestPick.storage_gb ? `${bestPick.storage_gb}GB` : "Not specified",
                    display: bestPick.screen_size || "Not specified",
                    battery: "Not specified",
                  },
                  reason: bestPick.short_reason || "Selected based on overall ranking performance.",
                  url: bestPick.url || undefined,
                }}
              />
            </section>
          )}

          <section>
            <h3 className="text-lg font-sans font-semibold text-zinc-900 mb-4">Alternative Options</h3>
            {alternatives.length === 0 ? (
              <div className="bg-white rounded-xl p-4 border border-zinc-200 text-sm text-zinc-500">
                No alternatives available.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {alternatives.map((alt) => (
                  <ProductCard
                    key={`${alt.store}-${alt.name}`}
                    product={{
                      id: `${alt.store}-${alt.name}`,
                      name: alt.name,
                      price: formatPrice(alt.price, alt.currency),
                      store: alt.store,
                      rating: alt.rating ?? 0,
                      score: alt.score ?? 0,
                      image: alt.image_url || fallbackImage(alt),
                      keySpec: `${alt.cpu || "Unknown CPU"}, ${alt.ram_gb ? `${alt.ram_gb}GB RAM` : "RAM n/a"}, ${alt.storage_gb ? `${alt.storage_gb}GB` : "Storage n/a"}`,
                      url: alt.url || undefined,
                      details: {
                        cpu: alt.cpu || "Not specified",
                        ram: alt.ram_gb ? `${alt.ram_gb}GB` : "Not specified",
                        storage: alt.storage_gb ? `${alt.storage_gb}GB` : "Not specified",
                        gpu: alt.gpu || "Not specified",
                        screen: alt.screen_size || "Not specified",
                        reason: alt.short_reason || "Alternative based on ranking.",
                      },
                    }}
                  />
                ))}
              </div>
            )}
          </section>

          <section>
            <h3 className="text-lg font-sans font-semibold text-zinc-900 mb-4">Comparison Table</h3>
            <ComparisonTable
              data={comparison.map((item, idx) => ({
                product: item.name,
                price: formatPrice(item.price, item.currency),
                ram: item.ram_gb ? `${item.ram_gb}GB` : "n/a",
                storage: item.storage_gb ? `${item.storage_gb}GB` : "n/a",
                cpu: item.cpu || "n/a",
                rating: item.rating ? `${item.rating}` : "n/a",
                score: item.score ? `${item.score.toFixed(2)}/10` : "n/a",
                isBest: idx === 0,
                url: item.url || undefined,
              }))}
            />
          </section>

          <section>
            <ReasoningPanel reasoning={result.reasoning} />
          </section>
        </div>
      )}
    </div>
  );
}
