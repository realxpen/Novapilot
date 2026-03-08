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
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-zinc-200 hover:border-indigo-300 transition-colors cursor-pointer group flex gap-5">
      <div className="relative w-24 h-24 rounded-xl overflow-hidden bg-zinc-100 flex-shrink-0">
        <Image
          src={product.image}
          alt={product.name}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-500"
          referrerPolicy="no-referrer"
        />
      </div>
      <div className="flex-1 min-w-0 flex flex-col justify-center">
        <h4 className="font-bold text-zinc-900 text-base truncate mb-1">
          {product.name}
        </h4>
        <div className="text-indigo-600 font-bold text-sm mb-1.5">
          {product.price}
        </div>
        <div className="text-xs text-zinc-500 truncate mb-3">
          {product.keySpec}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-zinc-600 bg-zinc-100 px-2 py-1 rounded-md flex items-center gap-1">
            <ShoppingCart className="w-3 h-3" />
            {product.store}
          </span>
          <span className="flex items-center gap-1 text-xs font-medium text-zinc-600">
            <Sparkles className="w-3 h-3 text-indigo-500" />
            Score: {product.score}
          </span>
        </div>
      </div>
    </div>
  );
}
