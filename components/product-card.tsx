"use client";

import { useEffect, useState } from "react";
import { ShoppingCart, Sparkles, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { getRepresentativeProductImage, resolveProductImage } from "./product-image-fallback";

interface ProductCardProps {
  product: {
    id: string;
    name: string;
    price: string;
    store: string;
    rating: number;
    score: number;
    image: string;
    keySpec: string;
    url?: string;
    details: {
      cpu: string;
      ram: string;
      storage: string;
      gpu: string;
      screen: string;
      reason: string;
    };
  };
}

export function ProductCard({ product }: ProductCardProps) {
  const [expanded, setExpanded] = useState(false);
  const fallbackImage = getRepresentativeProductImage(product.name);
  const [displayImage, setDisplayImage] = useState(() => resolveProductImage(product.image, product.name));
  const [fallbackTried, setFallbackTried] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setDisplayImage(resolveProductImage(product.image, product.name));
    setFallbackTried(false);
    setImageFailed(false);
  }, [product.image, product.name]);

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-zinc-200 hover:border-zinc-300 transition-colors group">
      <div className="flex gap-4">
        <div className="relative w-20 h-20 rounded-lg overflow-hidden bg-zinc-50 flex-shrink-0 border border-zinc-100">
          {!imageFailed ? (
            <img
              src={displayImage}
              alt={product.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              loading="lazy"
              onError={() => {
                if (!fallbackTried && displayImage !== fallbackImage) {
                  setDisplayImage(fallbackImage);
                  setFallbackTried(true);
                  return;
                }
                setImageFailed(true);
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-400 text-[10px] bg-zinc-100 px-1 text-center">
              No image
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <h4 className="font-semibold text-zinc-900 text-sm truncate mb-0.5">{product.name}</h4>
          <div className="text-zinc-900 font-bold text-sm mb-1">{product.price}</div>
          <div className="text-[11px] text-zinc-500 truncate mb-2">{product.keySpec}</div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[10px] font-medium text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded flex items-center gap-1">
              <ShoppingCart className="w-3 h-3" />
              {product.store}
            </span>
            <span className="flex items-center gap-1 text-[10px] font-medium text-zinc-500">
              <Sparkles className="w-3 h-3 text-zinc-400" />
              Score: {product.score.toFixed(2)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-xs px-2.5 py-1.5 rounded-md border border-zinc-300 hover:bg-zinc-50 text-zinc-700 flex items-center gap-1"
            >
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {expanded ? "Hide details" : "View details"}
            </button>

            {product.url && (
              <a
                href={product.url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-xs px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 text-white flex items-center gap-1"
              >
                Product page
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 p-3 rounded-lg border border-zinc-100 bg-zinc-50 text-xs text-zinc-700 space-y-1">
          <p><span className="font-semibold">CPU:</span> {product.details.cpu}</p>
          <p><span className="font-semibold">RAM:</span> {product.details.ram}</p>
          <p><span className="font-semibold">Storage:</span> {product.details.storage}</p>
          <p><span className="font-semibold">GPU:</span> {product.details.gpu}</p>
          <p><span className="font-semibold">Screen:</span> {product.details.screen}</p>
          <p><span className="font-semibold">Reason:</span> {product.details.reason}</p>
        </div>
      )}
    </div>
  );
}
