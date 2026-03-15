"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Navbar } from "@/components/navbar";
import { HomeSearch } from "@/components/home-search";
import {
  ResultsDashboard,
  type NovaPilotJobResponse,
} from "@/components/results-dashboard";

export default function Page() {
  const [appState, setAppState] = useState<"home" | "results">("home");
  const [searchQuery, setSearchQuery] = useState("");
  const [result, setResult] = useState<NovaPilotJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const defaultUserLocation =
    process.env.NEXT_PUBLIC_DEFAULT_USER_LOCATION?.trim() || "Nigeria";
  const requestTimeoutMs = 240000;

  const readApiError = async (response: Response): Promise<string> => {
    const fallback = `API request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown; message?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        return payload.detail;
      }
      if (typeof payload.message === "string" && payload.message.trim()) {
        return payload.message;
      }
      return fallback;
    } catch {
      return fallback;
    }
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    setError(null);
    setResult(null);
    setIsSubmitting(true);
    setAppState("results");

    const baseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

    try {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);
      try {
        const response = await fetch(`${baseUrl}/api/run-novapilot`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          signal: controller.signal,
          body: JSON.stringify({
            query,
            user_location: defaultUserLocation,
            top_n: 5,
          }),
        });
        window.clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(await readApiError(response));
        }

        const payload = (await response.json()) as NovaPilotJobResponse;
        setResult(payload);
        setIsSubmitting(false);
        setAppState("results");
      } finally {
        window.clearTimeout(timeoutId);
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError(
          "The request to the backend did not complete in time. Open the warning panel for the exact live extraction cause (for example Nova connectivity failure).",
        );
      } else {
        setError(err instanceof Error ? err.message : "Could not fetch recommendations");
      }
      setIsSubmitting(false);
      setAppState("results");
    }
  };

  const handleReset = () => {
    setSearchQuery("");
    setResult(null);
    setError(null);
    setIsSubmitting(false);
    setAppState("home");
  };

  useEffect(() => {
    if (!result?.job_id || result.status === "completed" || result.status === "failed") {
      return;
    }

    const baseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

    const interval = window.setInterval(async () => {
      try {
        const response = await fetch(`${baseUrl}/api/run-novapilot/${result.job_id}`);
        if (!response.ok) {
          if (response.status === 404) {
            setError("The live report session expired or the backend restarted. Run the search again.");
            setResult((current) =>
              current ? { ...current, status: "failed", error: "Job not found" } : current,
            );
          }
          return;
        }
        const payload = (await response.json()) as NovaPilotJobResponse;
        setResult(payload);
      } catch {
        // Best-effort polling; the dashboard already shows current status.
      }
    }, 4000);

    return () => window.clearInterval(interval);
  }, [result?.job_id, result?.status]);

  return (
    <div className="min-h-screen flex flex-col relative">
      <Navbar onReset={handleReset} />

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8 pt-32 pb-20">
        <AnimatePresence mode="wait">
          {appState === "home" && (
            <motion.div
              key="home"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="w-full max-w-4xl"
            >
              <HomeSearch onSearch={handleSearch} />
            </motion.div>
          )}

          {appState === "results" && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -30 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="w-full max-w-4xl"
            >
              <ResultsDashboard
                query={searchQuery}
                onReset={handleReset}
                result={result}
                error={error}
                isLoading={isSubmitting && !result && !error}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
