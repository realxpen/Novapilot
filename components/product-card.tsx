import { ShoppingCart, Sparkles } from "lucide-react";
import Image from "next/image";

interface ProductCardProps {
  product: {
    id: number;
    name: string;
    price: string;
    store: string;
    rating: number;
    score: number;
    image: string;
    keySpec: string;
  };
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-zinc-200 hover:border-zinc-300 transition-colors cursor-pointer group flex gap-4">
      <div className="relative w-20 h-20 rounded-lg overflow-hidden bg-zinc-50 flex-shrink-0 border border-zinc-100">
        <Image
          src={product.image}
          alt={product.name}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-500"
          referrerPolicy="no-referrer"
        />
      </div>
      <div className="flex-1 min-w-0 flex flex-col justify-center">
        <h4 className="font-semibold text-zinc-900 text-sm truncate mb-0.5">
          {product.name}
        </h4>
        <div className="text-zinc-900 font-bold text-sm mb-1">
          {product.price}
        </div>
        <div className="text-[11px] text-zinc-500 truncate mb-2">
          {product.keySpec}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded flex items-center gap-1">
            <ShoppingCart className="w-3 h-3" />
            {product.store}
          </span>
          <span className="flex items-center gap-1 text-[10px] font-medium text-zinc-500">
            <Sparkles className="w-3 h-3 text-zinc-400" />
            Score: {product.score}
          </span>
        </div>
      </div>
    </div>
  );
}
