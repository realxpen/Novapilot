import { Navbar } from "@/components/navbar";
import { Check, X } from "lucide-react";

export default function PricingPage() {
  const plans = [
    {
      name: "Free",
      price: "$0",
      description: "Perfect for occasional shoppers and basic research.",
      features: [
        { name: "5 AI searches per month", included: true },
        { name: "Standard product comparisons", included: true },
        { name: "Basic AI reasoning", included: true },
        { name: "Real-time price tracking", included: false },
        { name: "Priority support", included: false },
        { name: "API access", included: false },
      ],
      buttonText: "Get Started",
      buttonStyle:
        "bg-white text-zinc-900 border border-zinc-200 hover:bg-zinc-50",
    },
    {
      name: "Pro",
      price: "$12",
      period: "/month",
      description: "For power users who want the best deals, always.",
      features: [
        { name: "Unlimited AI searches", included: true },
        { name: "Advanced product comparisons", included: true },
        { name: "Deep AI reasoning & analysis", included: true },
        { name: "Real-time price tracking", included: true },
        { name: "Priority support", included: true },
        { name: "API access", included: true },
      ],
      buttonText: "Upgrade to Pro",
      buttonStyle: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-md",
      popular: true,
    },
  ];

  return (
    <div className="min-h-screen flex flex-col relative bg-zinc-50/50">
      <Navbar />

      <main className="flex-1 flex flex-col items-center pt-32 pb-20 px-4 sm:px-8">
        <div className="w-full max-w-4xl mx-auto text-center mb-16">
          <h1 className="text-4xl sm:text-6xl font-display font-bold tracking-tight text-zinc-900 mb-6">
            Simple, transparent pricing
          </h1>
          <p className="text-lg text-zinc-500 max-w-2xl mx-auto">
            Choose the plan that fits your shopping habits. No hidden fees, cancel anytime.
          </p>
        </div>

        <div className="w-full max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
          {plans.map((plan, index) => (
            <div
              key={index}
              className={`bg-white rounded-3xl p-8 sm:p-10 shadow-sm border relative flex flex-col ${
                plan.popular ? "border-indigo-600 ring-1 ring-indigo-600" : "border-zinc-200"
              }`}
            >
              {plan.popular && (
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-indigo-600 text-white text-xs font-bold uppercase tracking-wider py-1.5 px-4 rounded-full shadow-md">
                  Most Popular
                </div>
              )}
              <div className="mb-8">
                <h3 className="text-2xl font-bold text-zinc-900 mb-2">
                  {plan.name}
                </h3>
                <p className="text-zinc-500 mb-6">{plan.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-display font-bold text-zinc-900">
                    {plan.price}
                  </span>
                  {plan.period && (
                    <span className="text-zinc-500 font-medium">
                      {plan.period}
                    </span>
                  )}
                </div>
              </div>

              <ul className="space-y-4 mb-8 flex-1">
                {plan.features.map((feature, fIndex) => (
                  <li key={fIndex} className="flex items-center gap-3">
                    {feature.included ? (
                      <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                        <Check className="w-3 h-3 text-indigo-600" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">
                        <X className="w-3 h-3 text-zinc-400" />
                      </div>
                    )}
                    <span
                      className={`text-sm ${
                        feature.included ? "text-zinc-700 font-medium" : "text-zinc-400"
                      }`}
                    >
                      {feature.name}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                className={`w-full py-4 rounded-xl font-bold transition-colors ${plan.buttonStyle}`}
              >
                {plan.buttonText}
              </button>
            </div>
          ))}
        </div>

        <div className="w-full max-w-3xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-zinc-900 mb-8 text-center">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            {[
              {
                q: "What counts as an AI search?",
                a: "Any time you enter a query and NovaPilot analyzes the web to provide a recommendation, it counts as one search.",
              },
              {
                q: "Can I cancel my Pro subscription anytime?",
                a: "Yes, you can cancel your subscription at any time from your account settings. You will retain access to Pro features until the end of your billing cycle.",
              },
              {
                q: "How accurate are the prices?",
                a: "We pull prices in real-time from major retailers. However, prices can fluctuate rapidly, so we always recommend verifying the final price on the retailer's site before purchasing.",
              },
            ].map((faq, index) => (
              <div key={index} className="bg-white rounded-2xl p-6 shadow-sm border border-zinc-200">
                <h4 className="text-lg font-bold text-zinc-900 mb-2">{faq.q}</h4>
                <p className="text-zinc-500 leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
