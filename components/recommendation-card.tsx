import { Award, Sparkles, ShoppingCart, Star, Cpu, HardDrive, CheckCircle2, ExternalLink } from "lucide-react";
import Image from "next/image";

interface RecommendationCardProps {
  recommendation: {
    name: string;
    price: string;
    store: string;
    rating: number;
    score: number;
    image: string;
    specs: {
      cpu: string;
      ram: string;
      storage: string;
      display: string;
      battery: string;
    };
    reason: string;
  };
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  return (
    <div className="bg-white rounded-3xl shadow-xl border border-zinc-100 overflow-hidden relative group">
      <div className="absolute top-4 left-4 z-10 bg-indigo-600 text-white text-xs font-bold uppercase tracking-wider py-1.5 px-3 rounded-full shadow-md flex items-center gap-1.5">
        <Award className="w-4 h-4" />
        Top Pick
      </div>
      
      <div className="absolute top-4 right-4 z-10 bg-white/90 backdrop-blur-md text-indigo-700 text-sm font-bold py-1.5 px-3 rounded-full shadow-md flex items-center gap-1.5 border border-indigo-100">
        <Sparkles className="w-4 h-4 text-indigo-500" />
        AI Score: {recommendation.score}/100
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2">
        <div className="relative h-64 md:h-auto w-full bg-zinc-100">
          <Image
            src={recommendation.image}
            alt={recommendation.name}
            fill
            className="object-cover"
            referrerPolicy="no-referrer"
          />
        </div>

        <div className="p-8 flex flex-col justify-center">
          <div className="mb-4">
            <h2 className="text-3xl font-display font-bold text-zinc-900 mb-2">
              {recommendation.name}
            </h2>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="text-2xl font-bold text-indigo-600">
                {recommendation.price}
              </span>
              <span className="flex items-center gap-1 bg-zinc-100 text-zinc-700 px-2.5 py-1 rounded-md font-medium">
                <ShoppingCart className="w-4 h-4" />
                {recommendation.store}
              </span>
              <span className="flex items-center gap-1 bg-zinc-100 text-zinc-700 px-2.5 py-1 rounded-md font-medium">
                <Star className="w-4 h-4 fill-current text-yellow-500" />
                {recommendation.rating}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="flex flex-col gap-1 p-3 rounded-xl bg-zinc-50 border border-zinc-100">
              <Cpu className="w-4 h-4 text-indigo-500 mb-1" />
              <span className="text-xs text-zinc-500 font-medium">Processor</span>
              <span className="text-sm font-semibold text-zinc-900 truncate">{recommendation.specs.cpu}</span>
            </div>
            <div className="flex flex-col gap-1 p-3 rounded-xl bg-zinc-50 border border-zinc-100">
              <HardDrive className="w-4 h-4 text-indigo-500 mb-1" />
              <span className="text-xs text-zinc-500 font-medium">RAM & Storage</span>
              <span className="text-sm font-semibold text-zinc-900 truncate">{recommendation.specs.ram}</span>
            </div>
          </div>

          <div className="mb-6 bg-indigo-50/50 p-4 rounded-2xl border border-indigo-100/50">
            <h3 className="text-sm font-bold text-indigo-900 flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-indigo-600" />
              Why this was chosen
            </h3>
            <p className="text-sm text-indigo-800/80 leading-relaxed">
              {recommendation.reason}
            </p>
          </div>

          <button className="w-full py-3.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl font-medium transition-colors flex items-center justify-center gap-2 shadow-md">
            Buy on {recommendation.store}
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
