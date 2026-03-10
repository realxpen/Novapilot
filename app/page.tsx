"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Navbar } from "@/components/navbar";
import { HomeSearch } from "@/components/home-search";
import { ProgressTimeline } from "@/components/progress-timeline";
import {
  ResultsDashboard,
  type NovaPilotResponse,
} from "@/components/results-dashboard";

export default function Page() {
  const [appState, setAppState] = useState<"home" | "progress" | "results">(
    "home",
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [result, setResult] = useState<NovaPilotResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const defaultUserLocation =
    process.env.NEXT_PUBLIC_DEFAULT_USER_LOCATION?.trim() || "Nigeria";
  const requestTimeoutMs = 120000;

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    setError(null);
    setResult(null);
    setAppState("progress");

    const baseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

    try {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);
      const response = await fetch(`${baseUrl}/api/run-novapilot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        signal: controller.signal,
        body: JSON.stringify({
          query,
          user_location: defaultUserLocation,
          top_n: 3,
        }),
      });
      window.clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }

      const payload = (await response.json()) as NovaPilotResponse;
      setResult(payload);
      setAppState("results");
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError("Recommendation request timed out. Check your live Nova Act workflow configuration and try fewer stores.");
      } else {
        setError(err instanceof Error ? err.message : "Could not fetch recommendations");
      }
      setAppState("results");
    }
  };

  const handleReset = () => {
    setSearchQuery("");
    setResult(null);
    setError(null);
    setAppState("home");
  };

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

          {appState === "progress" && (
            <motion.div
              key="progress"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="w-full max-w-4xl"
            >
              <ProgressTimeline query={searchQuery} />
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
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
