"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Navbar } from "@/components/navbar";
import { HomeSearch } from "@/components/home-search";
import { ProgressTimeline } from "@/components/progress-timeline";
import { ResultsDashboard } from "@/components/results-dashboard";

export default function Page() {
  const [appState, setAppState] = useState<"home" | "progress" | "results">(
    "home",
  );
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setAppState("progress");

    // Simulate AI processing time
    setTimeout(() => {
      setAppState("results");
    }, 6000);
  };

  const handleReset = () => {
    setSearchQuery("");
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
              <ResultsDashboard query={searchQuery} onReset={handleReset} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
