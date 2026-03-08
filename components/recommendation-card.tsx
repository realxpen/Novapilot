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
    <div className="bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden relative group">
      <div className="absolute top-3 left-3 z-10 bg-zinc-900 text-white text-[10px] font-bold uppercase tracking-wider py-1 px-2 rounded flex items-center gap-1">
        <Award className="w-3 h-3" />
        Top Pick
      </div>
      
      <div className="absolute top-3 right-3 z-10 bg-white/90 backdrop-blur-md text-zinc-900 text-xs font-semibold py-1 px-2 rounded shadow-sm flex items-center gap-1 border border-zinc-200">
        <Sparkles className="w-3 h-3 text-zinc-500" />
        Score: {recommendation.score}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5">
        <div className="relative h-48 md:h-auto md:col-span-2 w-full bg-zinc-50 border-b md:border-b-0 md:border-r border-zinc-100">
          <Image
            src={recommendation.image}
            alt={recommendation.name}
            fill
            className="object-cover"
            referrerPolicy="no-referrer"
          />
        </div>

        <div className="p-6 md:col-span-3 flex flex-col justify-center">
          <div className="mb-4">
            <h2 className="text-xl font-sans font-semibold text-zinc-900 mb-1">
              {recommendation.name}
            </h2>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-lg font-bold text-zinc-900">
                {recommendation.price}
              </span>
              <span className="flex items-center gap-1 text-zinc-500 font-medium ml-2">
                <ShoppingCart className="w-3 h-3" />
                {recommendation.store}
              </span>
              <span className="flex items-center gap-1 text-zinc-500 font-medium">
                <Star className="w-3 h-3 fill-current text-zinc-400" />
                {recommendation.rating}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-5">
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">Processor</span>
              <span className="text-sm font-medium text-zinc-800 truncate flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-zinc-400" />
                {recommendation.specs.cpu}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">Memory</span>
              <span className="text-sm font-medium text-zinc-800 truncate flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-zinc-400" />
                {recommendation.specs.ram}
              </span>
            </div>
          </div>

          <div className="mb-5 bg-zinc-50 p-3 rounded-lg border border-zinc-100">
            <h3 className="text-xs font-semibold text-zinc-900 flex items-center gap-1.5 mb-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-zinc-500" />
              Why this was chosen
            </h3>
            <p className="text-xs text-zinc-600 leading-relaxed">
              {recommendation.reason}
            </p>
          </div>

          <button className="w-full py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 shadow-sm">
            Buy on {recommendation.store}
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
