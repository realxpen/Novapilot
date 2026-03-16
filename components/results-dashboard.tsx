"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Circle,
  Cpu,
  ExternalLink,
  Loader2,
  Search,
  ShieldCheck,
} from "lucide-react";
import { RecommendationCard } from "./recommendation-card";
import { ProductCard } from "./product-card";
import { ComparisonTable } from "./comparison-table";
import { ReasoningPanel } from "./reasoning-panel";
import { getRepresentativeProductImage, resolveProductImage } from "./product-image-fallback";

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

export interface InstantGuidance {
  headline: string;
  summary: string;
  key_specs: string[];
  target_models: string[];
  featured_recommendations: string[];
  market_insights: string[];
  budget_bands: string[];
  budget_note: string;
  selected_sites: string[];
  next_step: string;
}

export interface NovaPilotJobResponse {
  job_id: string;
  status: string;
  query: string;
  interpreted_request: NovaPilotResponse["interpreted_request"];
  instant_guidance: InstantGuidance;
  current_step?: string | null;
  execution_log?: NovaPilotResponse["execution_log"];
  final_report?: NovaPilotResponse | null;
  error?: string | null;
}

interface ResultsDashboardProps {
  query: string;
  onReset: () => void;
  result: NovaPilotJobResponse | null;
  error: string | null;
  isLoading?: boolean;
}

interface GuidanceCard {
  model: string;
  subtitle: string;
  image: string;
}

const GUIDANCE_REFERENCE_IMAGES: Record<string, GuidanceCard> = {
  thinkpad: {
    model: "ThinkPad Series",
    subtitle: "Developer-first keyboard and upgrade-friendly chassis",
    image:
      "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1200&q=80",
  },
  elitebook: {
    model: "HP EliteBook Line",
    subtitle: "Business-grade build quality with strong everyday performance",
    image:
      "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1200&q=80",
  },
  latitude: {
    model: "Dell Latitude Line",
    subtitle: "Reliable coding machine for multitasking and long sessions",
    image:
      "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?auto=format&fit=crop&w=1200&q=80",
  },
  macbook: {
    model: "MacBook Air",
    subtitle: "Excellent battery life and strong fit for mobile development",
    image:
      "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
  },
  tablet: {
    model: "Tablet Series",
    subtitle: "Portable large-screen devices suited for sketching and design workflows",
    image:
      "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1200&q=80",
  },
  smartphone: {
    model: "Phone Series",
    subtitle: "Strong everyday performance with solid cameras and battery life",
    image:
      "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
  },
  audio: {
    model: "Audio Series",
    subtitle: "Comfort, sound quality, and battery life for daily listening",
    image:
      "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
  },
  default: {
    model: "Laptop Target",
    subtitle: "Reference image for the recommended product family",
    image:
      "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=1200&q=80",
  },
};

function easeInOutCubic(value: number): number {
  if (value < 0.5) {
    return 4 * value * value * value;
  }
  return 1 - Math.pow(-2 * value + 2, 3) / 2;
}

function animateViewportTo(element: HTMLElement | null, offset = 24, duration = 900): void {
  if (!element || typeof window === "undefined") {
    return;
  }

  const startY = window.scrollY;
  const targetY = Math.max(0, window.scrollY + element.getBoundingClientRect().top - offset);
  const distance = targetY - startY;

  if (Math.abs(distance) < 8) {
    return;
  }

  let frameId = 0;
  const startedAt = performance.now();

  const tick = (now: number) => {
    const elapsed = now - startedAt;
    const progress = Math.min(elapsed / duration, 1);
    const eased = easeInOutCubic(progress);
    window.scrollTo({ top: startY + distance * eased, behavior: "auto" });

    if (progress < 1) {
      frameId = window.requestAnimationFrame(tick);
    }
  };

  frameId = window.requestAnimationFrame(tick);

  window.setTimeout(() => {
    if (frameId) {
      window.cancelAnimationFrame(frameId);
    }
  }, duration + 120);
}

function formatPrice(price: number, currency: string): string {
  const locale = currency.toUpperCase() === "NGN" ? "en-NG" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: currency.toUpperCase(),
    maximumFractionDigits: 0,
  }).format(price);
}

function normalizeRecommendationKey(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatWarningMessage(warning: string): string {
  const lowered = warning.toLowerCase();
  if (
    lowered.includes("automation failed before extraction") &&
    lowered.includes("nova act actuator could not start")
  ) {
    const store = warning.split(" automation failed before extraction")[0]?.trim() || "A store";
    return `${store} live extraction is temporarily unavailable, so the report is using the remaining live store results plus reference recommendations where needed.`;
  }
  return warning;
}

function fallbackProductImage(product: Product): string {
  return getRepresentativeProductImage(product.name);
}

function pickGuidanceImage(model: string): GuidanceCard {
  const normalized = model.toLowerCase();
  if (normalized.includes("thinkpad")) {
    return GUIDANCE_REFERENCE_IMAGES.thinkpad;
  }
  if (normalized.includes("elitebook") || normalized.includes("hp")) {
    return GUIDANCE_REFERENCE_IMAGES.elitebook;
  }
  if (normalized.includes("latitude") || normalized.includes("dell")) {
    return GUIDANCE_REFERENCE_IMAGES.latitude;
  }
  if (normalized.includes("macbook")) {
    return GUIDANCE_REFERENCE_IMAGES.macbook;
  }
  if (
    normalized.includes("ipad") ||
    normalized.includes("tab ") ||
    normalized.includes("tablet") ||
    normalized.includes("pad ")
  ) {
    return GUIDANCE_REFERENCE_IMAGES.tablet;
  }
  if (
    normalized.includes("galaxy a") ||
    normalized.includes("pixel") ||
    normalized.includes("redmi") ||
    normalized.includes("infinix") ||
    normalized.includes("tecno")
  ) {
    return GUIDANCE_REFERENCE_IMAGES.smartphone;
  }
  if (
    normalized.includes("sony wh") ||
    normalized.includes("soundcore") ||
    normalized.includes("jbl") ||
    normalized.includes("headphone")
  ) {
    return GUIDANCE_REFERENCE_IMAGES.audio;
  }
  return GUIDANCE_REFERENCE_IMAGES.default;
}

function buildPendingSteps(
  sites: string[],
  hasReport: boolean,
  progressItems: NovaPilotResponse["execution_log"] = [],
) {
  if (progressItems.length > 0) {
    const merged = new Map<
      string,
      {
        id: string;
        label: string;
        state: "complete" | "failed" | "active";
        lastTimestamp: string;
      }
    >();

    for (const item of progressItems) {
      const state =
        item.status === "completed"
          ? ("complete" as const)
          : item.status === "failed"
            ? ("failed" as const)
            : ("active" as const);
      const current = merged.get(item.step_id);
      if (!current) {
        merged.set(item.step_id, {
          id: item.step_id,
          label: item.label,
          state,
          lastTimestamp: item.timestamp,
        });
        continue;
      }
      current.label = item.label;
      current.state = state;
      current.lastTimestamp = item.timestamp;
    }

    return Array.from(merged.values()).map(({ id, label, state }) => ({
      id,
      label,
      state,
    }));
  }

  const storeSteps = sites.map((site) => ({
    id: site,
    label: `Searching ${site.charAt(0).toUpperCase()}${site.slice(1)}`,
  }));

  const steps = [
    { id: "understanding", label: "Understanding request" },
    ...storeSteps,
    { id: "extracting", label: "Extracting product details" },
    { id: "comparing", label: "Comparing results" },
    { id: "generating", label: "Generating recommendation" },
  ];

  return steps.map((step, index) => {
    if (hasReport) {
      return { ...step, state: "complete" as const };
    }
    if (index === 0) {
      return { ...step, state: "complete" as const };
    }
    if (index === 1) {
      return { ...step, state: "active" as const };
    }
    return { ...step, state: "pending" as const };
  });
}

function buildCurrentStatus(
  fallbackStatus: string,
  nextStep: string,
  progressItems: NovaPilotResponse["execution_log"] = [],
) {
  if (progressItems.length === 0) {
    return {
      title: fallbackStatus,
      body: nextStep,
    };
  }

  const latest = [...progressItems].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).at(-1);
  if (!latest) {
    return {
      title: fallbackStatus,
      body: nextStep,
    };
  }

  const body =
    typeof latest.details?.error === "string" && latest.details.error
      ? latest.details.error
      : latest.status === "completed"
        ? "Completed."
        : latest.status === "failed"
          ? "Failed."
          : "Working on this step now.";

  return {
    title: latest.label,
    body,
  };
}

function WaitingState({
  query,
  sites,
  status,
  nextStep,
  finalPreview,
  progressItems,
}: {
  query: string;
  sites: string[];
  status: string;
  nextStep: string;
  finalPreview: Product[];
  progressItems?: NovaPilotResponse["execution_log"];
}) {
  const steps = buildPendingSteps(sites, finalPreview.length > 0, progressItems);
  const currentStatus = buildCurrentStatus(status, nextStep, progressItems);

  return (
    <section className="overflow-hidden rounded-[28px] border border-zinc-200 bg-white shadow-[0_24px_80px_-40px_rgba(15,23,42,0.35)]">
      <div className="grid gap-0 md:grid-cols-[1.55fr_0.95fr]">
        <div className="border-b border-zinc-100 p-7 md:border-b-0 md:border-r">
          <div className="mb-7">
            <h3 className="flex items-center gap-2 text-[28px] font-semibold tracking-tight text-zinc-950">
              <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
              Researching
            </h3>
            <p className="mt-2 max-w-xl text-sm text-zinc-500">&quot;{query}&quot;</p>
          </div>

          <div className="space-y-4">
            {steps.map((step) => (
              <div key={step.id} className="flex items-center gap-3 text-sm">
                {step.state === "complete" ? (
                  <CheckCircle2 className="h-4 w-4 text-zinc-900" />
                ) : step.state === "failed" ? (
                  <AlertTriangle className="h-4 w-4 text-rose-700" />
                ) : step.state === "active" ? (
                  <Loader2 className="h-4 w-4 animate-spin text-zinc-900" />
                ) : (
                  <Circle className="h-4 w-4 text-zinc-300" />
                )}
                <span
                  className={
                    step.state === "pending"
                      ? "text-zinc-400"
                      : "font-medium text-zinc-800"
                  }
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-zinc-50/70 p-7">
          <div className="mb-5 flex items-center justify-between">
            <h4 className="flex items-center gap-2 text-sm font-medium text-zinc-900">
              <Search className="h-4 w-4 text-zinc-500" />
              Live Extractions
            </h4>
            <span className="rounded-full bg-zinc-200/80 px-2.5 py-1 text-[11px] font-medium text-zinc-600">
              {finalPreview.length} items
            </span>
          </div>

          {finalPreview.length === 0 ? (
            <div className="flex min-h-[182px] flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-200 bg-white px-6 text-center">
              <Search className="mb-3 h-5 w-5 text-zinc-300" />
              <p className="text-xs text-zinc-500">Waiting for agent to find products...</p>
            </div>
          ) : (
            <div className="space-y-3">
              {finalPreview.map((product) => (
                <div
                  key={`${product.store}-${product.name}`}
                  className="flex gap-3 rounded-2xl border border-zinc-200 bg-white p-2.5"
                >
                  <div className="h-14 w-14 overflow-hidden rounded-xl bg-zinc-100">
                    <img
                      src={resolveProductImage(product.image_url, product.name)}
                      alt={product.name}
                      className="h-full w-full object-cover"
                      loading="lazy"
                      onError={(event) => {
                        const imageElement = event.currentTarget;
                        if (imageElement.dataset.fallbackApplied === "1") {
                          return;
                        }
                        imageElement.dataset.fallbackApplied = "1";
                        imageElement.src = fallbackProductImage(product);
                      }}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-zinc-900">{product.name}</p>
                    <p className="mt-1 text-xs font-semibold text-zinc-950">
                      {formatPrice(product.price, product.currency)}
                    </p>
                    <p className="mt-1 text-[11px] text-zinc-500">{product.store}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-5 rounded-2xl border border-zinc-200 bg-white px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-400">Current status</p>
            <p className="mt-1 text-sm font-medium text-zinc-900">{currentStatus.title}</p>
            <p className="mt-2 text-xs leading-relaxed text-zinc-500">{currentStatus.body}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function ResultsDashboard({
  query,
  onReset,
  result,
  error,
  isLoading = false,
}: ResultsDashboardProps) {
  const [failedGuidanceImages, setFailedGuidanceImages] = useState<Record<string, boolean>>({});
  const waitingRef = useRef<HTMLElement | null>(null);
  const recommendationRef = useRef<HTMLElement | null>(null);
  const lastResearchScrollJobRef = useRef<string | null>(null);
  const lastAutoScrollKeyRef = useRef<string | null>(null);

  const report = result?.final_report ?? null;
  const bestPick = report?.best_pick ?? null;
  const alternatives = report?.alternatives ?? [];
  const minimumRecommendationCount = 3;
  const comparison = report?.comparison_table ?? [];
  const reportHasProducts = Boolean(bestPick) || comparison.length > 0;
  const primaryReportWarning =
    report?.warnings?.find((warning) => warning.trim().length > 0) ?? null;
  const showWaitingState =
    Boolean(result) &&
    !report &&
    result?.status !== "failed" &&
    result?.status !== "completed";

  const guidanceCards = useMemo(
    () =>
      (result?.instant_guidance.target_models ?? []).map((model) => {
        const reference = pickGuidanceImage(model);
        return {
          ...reference,
          model,
        };
      }),
    [result?.instant_guidance.target_models],
  );

  const livePreview = useMemo(() => {
    if (!report) {
      return [];
    }

    const preview: Product[] = [];
    if (report.best_pick) {
      preview.push(report.best_pick);
    }
    for (const alt of report.alternatives) {
      if (preview.length >= 3) {
        break;
      }
      preview.push(alt);
    }
    return preview;
  }, [report]);

  const supplementalAlternativeCards = useMemo(() => {
    if (!report || !bestPick) {
      return [];
    }

    const liveCount = 1 + alternatives.length;
    if (liveCount >= minimumRecommendationCount) {
      return [];
    }

    const existingKeys = new Set(
      [bestPick.name, ...alternatives.map((item) => item.name)].map(normalizeRecommendationKey),
    );

    return guidanceCards
      .filter((card) => {
        const candidateKey = normalizeRecommendationKey(card.model);
        return !Array.from(existingKeys).some(
          (existingKey) =>
            existingKey === candidateKey ||
            existingKey.includes(candidateKey) ||
            candidateKey.includes(existingKey),
        );
      })
      .slice(0, minimumRecommendationCount - liveCount)
      .map((card, index) => ({
        id: `reference-${card.model}-${index}`,
        name: card.model,
        price: "Check live stores",
        store: "reference",
        rating: 0,
        score: 0,
        image: card.image,
        keySpec: card.subtitle,
        url: undefined,
        details: {
          cpu: "Varies by listing",
          ram: "Varies by listing",
          storage: "Varies by listing",
          gpu: "Varies by listing",
          screen: "Varies by listing",
          reason:
            "Reference model family added because the live report returned fewer than 3 valid store listings.",
        },
      }));
  }, [alternatives, bestPick, guidanceCards, report]);

  const displayedAlternativeCards = useMemo(() => {
    const liveCards = alternatives.map((alt) => ({
      id: `${alt.store}-${alt.name}`,
      name: alt.name,
      price: formatPrice(alt.price, alt.currency),
      store: alt.store,
      rating: alt.rating ?? 0,
      score: alt.score ?? 0,
      image: resolveProductImage(alt.image_url, alt.name),
      keySpec: `${alt.cpu || "Unknown CPU"}, ${
        alt.ram_gb ? `${alt.ram_gb}GB RAM` : "RAM n/a"
      }, ${alt.storage_gb ? `${alt.storage_gb}GB` : "Storage n/a"}`,
      url: alt.url || undefined,
      details: {
        cpu: alt.cpu || "Not specified",
        ram: alt.ram_gb ? `${alt.ram_gb}GB` : "Not specified",
        storage: alt.storage_gb ? `${alt.storage_gb}GB` : "Not specified",
        gpu: alt.gpu || "Not specified",
        screen: alt.screen_size || "Not specified",
        reason: alt.short_reason || "Alternative based on ranking.",
      },
    }));

    return [...liveCards, ...supplementalAlternativeCards];
  }, [alternatives, supplementalAlternativeCards]);

  useEffect(() => {
    if (!showWaitingState || !result?.job_id) {
      lastResearchScrollJobRef.current = null;
      return;
    }

    if (lastResearchScrollJobRef.current === result.job_id) {
      return;
    }
    lastResearchScrollJobRef.current = result.job_id;

    const timeoutId = window.setTimeout(() => {
      animateViewportTo(waitingRef.current, 28, 1150);
    }, 900);

    return () => window.clearTimeout(timeoutId);
  }, [result?.job_id, showWaitingState]);

  useEffect(() => {
    if (!reportHasProducts) {
      lastAutoScrollKeyRef.current = null;
      return;
    }

    const scrollKey = `${query}-${bestPick?.name ?? "comparison"}-${comparison.length}`;
    if (lastAutoScrollKeyRef.current === scrollKey) {
      return;
    }
    lastAutoScrollKeyRef.current = scrollKey;

    const timeoutId = window.setTimeout(() => {
      animateViewportTo(recommendationRef.current, 28, 1050);
    }, 550);

    return () => window.clearTimeout(timeoutId);
  }, [bestPick?.name, comparison.length, query, reportHasProducts]);

  return (
    <div className="mx-auto w-full max-w-5xl pb-20">
      <div className="mb-8 flex items-center justify-between gap-4">
        <button
          onClick={onReset}
          className="flex items-center gap-2 text-sm font-medium text-zinc-500 transition-colors hover:text-zinc-900"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Search
        </button>
        <div className="flex max-w-md items-center gap-2 rounded-full border border-zinc-200 bg-white/90 px-4 py-2 text-sm text-zinc-600 shadow-sm">
          <span className="font-semibold text-zinc-900">Query</span>
          <span className="truncate">&quot;{query}&quot;</span>
        </div>
      </div>

      {error && (
        <div className="mb-6 flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {report?.warnings && report.warnings.length > 0 && (
        <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4" />
            <div className="space-y-1">
              {report.warnings.map((warning, index) => (
                <p key={`${warning}-${index}`} className="text-sm">
                  {formatWarningMessage(warning)}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {result?.status === "failed" && result.error && (
        <div className="mb-6 flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-900">
          <AlertTriangle className="mt-0.5 h-4 w-4" />
          <p className="text-sm">{result.error}</p>
        </div>
      )}

      {!result && !error && isLoading && (
        <WaitingState
          query={query}
          sites={["jumia"]}
          status="starting"
          nextStep="Preparing your instant guidance and starting the live market report."
          finalPreview={[]}
        />
      )}

      {!result && !error && !isLoading && (
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 text-sm text-zinc-600">
          No result available yet. Submit a query to fetch recommendations.
        </div>
      )}

      {result && (
        <div className="space-y-8">
          <section className="overflow-hidden rounded-[32px] border border-zinc-200 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_36%),linear-gradient(135deg,#0f172a_0%,#1f2937_42%,#fafaf9_100%)] p-[1px] shadow-[0_28px_80px_-40px_rgba(15,23,42,0.55)]">
            <div className="rounded-[31px] bg-white/96 p-7 backdrop-blur">
              <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-800">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Best-fit guidance
                  </div>
                  <h2 className="mt-4 text-3xl font-semibold tracking-tight text-zinc-950 sm:text-4xl">
                    {result.instant_guidance.headline}
                  </h2>
                  <p className="mt-4 max-w-2xl text-sm leading-7 text-zinc-600">
                    {result.instant_guidance.summary}
                  </p>

                  <div className="mt-6 flex flex-wrap gap-2">
                    {result.instant_guidance.key_specs.map((spec) => (
                      <span
                        key={spec}
                        className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs font-medium text-zinc-700"
                      >
                        {spec}
                      </span>
                    ))}
                  </div>

                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-3xl border border-zinc-200 bg-zinc-50 p-5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                        What to target
                      </p>
                      <div className="mt-4 space-y-3">
                        {result.instant_guidance.target_models.map((model) => (
                          <div key={model} className="rounded-2xl bg-white px-4 py-3 shadow-sm">
                            <p className="font-medium text-zinc-900">{model}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-3xl border border-zinc-200 bg-zinc-950 p-5 text-white">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                        Market read
                      </p>
                      <p className="mt-4 text-sm leading-7 text-zinc-200">
                        {result.instant_guidance.budget_note}
                      </p>
                      <div className="mt-6 space-y-3">
                        <div className="rounded-2xl bg-white/10 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-zinc-400">Live stores</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {result.instant_guidance.selected_sites.map((site) => (
                              <span
                                key={site}
                                className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white"
                              >
                                {site}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-2xl bg-amber-400/15 px-4 py-3 text-amber-100">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-amber-200/80">
                            Detailed report
                          </p>
                          <p className="mt-2 text-sm leading-6">{result.instant_guidance.next_step}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4 lg:grid-cols-3">
                    <div className="rounded-3xl border border-zinc-200 bg-white p-5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                        Top picks now
                      </p>
                      <div className="mt-4 space-y-3 text-sm text-zinc-700">
                        {result.instant_guidance.featured_recommendations.map((item) => (
                          <div key={item} className="rounded-2xl bg-zinc-50 px-4 py-3">
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-3xl border border-zinc-200 bg-white p-5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                        Market signals
                      </p>
                      <div className="mt-4 space-y-3 text-sm text-zinc-700">
                        {result.instant_guidance.market_insights.map((item) => (
                          <div key={item} className="rounded-2xl bg-zinc-50 px-4 py-3">
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-3xl border border-zinc-200 bg-white p-5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                        Budget bands
                      </p>
                      <div className="mt-4 space-y-3 text-sm text-zinc-700">
                        {result.instant_guidance.budget_bands.map((item) => (
                          <div key={item} className="rounded-2xl bg-zinc-50 px-4 py-3">
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4">
                  {guidanceCards.map((card) => {
                    const failed = failedGuidanceImages[card.model] ?? false;

                    return (
                      <article
                        key={card.model}
                        className="overflow-hidden rounded-[28px] border border-zinc-200 bg-zinc-950 text-white shadow-[0_18px_60px_-35px_rgba(15,23,42,0.9)]"
                      >
                        <div className="relative h-40 overflow-hidden">
                          {!failed ? (
                            <img
                              src={card.image}
                              alt={`${card.model} reference`}
                              className="h-full w-full object-cover opacity-80"
                              loading="lazy"
                              referrerPolicy="no-referrer"
                              onError={() =>
                                setFailedGuidanceImages((current) => ({
                                  ...current,
                                  [card.model]: true,
                                }))
                              }
                            />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center bg-[linear-gradient(135deg,#18181b_0%,#3f3f46_100%)] px-6 text-center">
                              <p className="text-sm text-zinc-200">{card.model}</p>
                            </div>
                          )}
                          <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent" />
                          <div className="absolute left-4 top-4 rounded-full bg-white/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white backdrop-blur">
                            Reference family
                          </div>
                          <div className="absolute bottom-4 left-4 right-4">
                            <p className="text-lg font-semibold">{card.model}</p>
                            <p className="mt-1 text-sm text-zinc-300">{card.subtitle}</p>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>

          {showWaitingState && (
            <section ref={waitingRef} className="relative">
              <div className="pointer-events-none absolute left-1/2 top-0 hidden -translate-x-1/2 -translate-y-1/2 md:flex">
                <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/95 px-4 py-2 text-xs font-medium text-zinc-600 shadow-lg shadow-zinc-950/5 backdrop-blur">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-zinc-900" />
                  Live research continuing below
                </div>
              </div>
              <WaitingState
                query={query}
                sites={result.instant_guidance.selected_sites}
                status={result.current_step || result.status}
                nextStep={result.instant_guidance.next_step}
                finalPreview={livePreview}
                progressItems={result.execution_log}
              />
            </section>
          )}

          {result?.status === "failed" && !report && (
            <section className="rounded-[28px] border border-rose-200 bg-rose-50 p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-rose-100 p-3">
                  <AlertTriangle className="h-5 w-5 text-rose-700" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-rose-950">Live extraction did not finish cleanly</h3>
                  <p className="mt-1 text-sm leading-6 text-rose-900">
                    The market report stopped before valid products were returned.
                  </p>
                  <p className="mt-3 text-sm text-rose-800">
                    {result.error || "The live workflow failed before the final report could be generated."}
                  </p>
                </div>
              </div>
            </section>
          )}

          {bestPick && (
            <section ref={recommendationRef}>
              <RecommendationCard
                recommendation={{
                  name: bestPick.name,
                  price: formatPrice(bestPick.price, bestPick.currency),
                  store: bestPick.store,
                  rating: bestPick.rating ?? 0,
                  score: bestPick.score ?? 0,
                  image: resolveProductImage(bestPick.image_url, bestPick.name),
                  specs: {
                    cpu: bestPick.cpu || "Not specified",
                    ram: bestPick.ram_gb ? `${bestPick.ram_gb}GB` : "Not specified",
                    storage: bestPick.storage_gb ? `${bestPick.storage_gb}GB` : "Not specified",
                    display: bestPick.screen_size || "Not specified",
                    battery: "Not specified",
                  },
                  reason:
                    bestPick.short_reason || "Selected based on overall ranking performance.",
                  url: bestPick.url || undefined,
                }}
              />
            </section>
          )}

          {report && !reportHasProducts && (
            <section className="rounded-[28px] border border-rose-200 bg-rose-50 p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-rose-100 p-3">
                  <AlertTriangle className="h-5 w-5 text-rose-700" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-rose-950">Live extraction did not finish cleanly</h3>
                  <p className="mt-1 text-sm leading-6 text-rose-900">
                    {primaryReportWarning ||
                      "The agent did not return enough valid product pages for a final recommendation."}
                  </p>
                  {report.warnings && report.warnings.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {report.warnings.map((warning, index) => (
                        <p key={`${warning}-${index}`} className="text-sm text-rose-800">
                          {formatWarningMessage(warning)}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {report && reportHasProducts && (
            <section>
              <div className="mb-4 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900">Alternative Options</h3>
                  <p className="mt-1 text-sm text-zinc-500">
                    {supplementalAlternativeCards.length > 0
                      ? "Live listings first, with reference model families added when fewer than 3 valid store results were available."
                      : "Real listings pulled from the product pages that matched this search."}
                  </p>
                </div>
              </div>
              {displayedAlternativeCards.length === 0 ? (
                <div className="rounded-2xl border border-zinc-200 bg-white p-4 text-sm text-zinc-500">
                  No alternatives available.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {displayedAlternativeCards.map((alt) => (
                    <ProductCard
                      key={alt.id}
                      product={alt}
                    />
                  ))}
                </div>
              )}
            </section>
          )}

          {report && reportHasProducts && (
            <section className="rounded-[28px] border border-zinc-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900">Comparison Table</h3>
                  <p className="mt-1 text-sm text-zinc-500">
                    Exact prices, hardware, and store links from the live report.
                  </p>
                </div>
                {bestPick?.url && (
                  <a
                    href={bestPick.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-2 rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:border-zinc-300 hover:text-zinc-950"
                  >
                    Open top pick
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
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
          )}

          {report && (
            <section className="rounded-[28px] border border-zinc-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <div className="rounded-2xl bg-zinc-100 p-3">
                  <Cpu className="h-5 w-5 text-zinc-700" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900">Why these made the cut</h3>
                  <p className="mt-1 text-sm text-zinc-500">
                    Final reasoning based on the live product pages and the original intent.
                  </p>
                </div>
              </div>
              <ReasoningPanel reasoning={report.reasoning} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}
