import { Navbar } from "@/components/navbar";
import { Search, Brain, Award, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function HowItWorksPage() {
  const steps = [
    {
      icon: <Search className="w-8 h-8 text-indigo-600" />,
      title: "1. Tell us what you need",
      description:
        "Describe what you're looking for in plain English. Whether it's 'a laptop for video editing under $1000' or 'the best noise-canceling headphones for travel', NovaPilot understands your intent.",
    },
    {
      icon: <Brain className="w-8 h-8 text-indigo-600" />,
      title: "2. AI analyzes the web",
      description:
        "Our advanced AI agent scours the internet, reading reviews, comparing specs, and checking prices across multiple retailers in real-time to find the best options.",
    },
    {
      icon: <Award className="w-8 h-8 text-indigo-600" />,
      title: "3. Get the perfect recommendation",
      description:
        "Receive a curated list of top picks, complete with a detailed comparison table, pros and cons, and a transparent explanation of exactly why the AI chose them.",
    },
  ];

  return (
    <div className="min-h-screen flex flex-col relative bg-zinc-50/50">
      <Navbar />

      <main className="flex-1 flex flex-col items-center pt-32 pb-20 px-4 sm:px-8">
        <div className="w-full max-w-4xl mx-auto text-center mb-16">
          <h1 className="text-4xl sm:text-6xl font-display font-bold tracking-tight text-zinc-900 mb-6">
            How NovaPilot Works
          </h1>
          <p className="text-lg text-zinc-500 max-w-2xl mx-auto">
            We've combined advanced AI reasoning with real-time web search to
            completely automate the tedious process of product research.
          </p>
        </div>

        <div className="w-full max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
          {steps.map((step, index) => (
            <div
              key={index}
              className="bg-white rounded-3xl p-8 shadow-sm border border-zinc-200 flex flex-col items-center text-center relative overflow-hidden group hover:border-indigo-200 transition-colors"
            >
              <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                {step.icon}
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-4">
                {step.title}
              </h3>
              <p className="text-zinc-500 leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>

        <div className="bg-indigo-600 rounded-3xl p-10 sm:p-16 w-full max-w-5xl mx-auto text-center text-white shadow-xl relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('https://picsum.photos/seed/abstract/1920/1080')] opacity-10 mix-blend-overlay object-cover" />
          <div className="relative z-10">
            <h2 className="text-3xl sm:text-4xl font-display font-bold mb-6">
              Ready to find your next favorite product?
            </h2>
            <p className="text-indigo-100 text-lg mb-8 max-w-2xl mx-auto">
              Stop spending hours reading reviews and comparing specs. Let NovaPilot do the heavy lifting for you.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 bg-white text-indigo-600 px-8 py-4 rounded-full font-bold hover:bg-indigo-50 transition-colors shadow-lg"
            >
              Try NovaPilot Now
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
