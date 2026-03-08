import { Award, Star } from "lucide-react";

interface ComparisonTableProps {
  data: {
    product: string;
    price: string;
    ram: string;
    storage: string;
    cpu: string;
    rating: string;
    score: string;
    isBest: boolean;
  }[];
}

export function ComparisonTable({ data }: ComparisonTableProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-[11px] text-zinc-500 uppercase tracking-wider bg-zinc-50/50 border-b border-zinc-200">
            <tr>
              <th className="px-6 py-3 font-medium">Product</th>
              <th className="px-6 py-3 font-medium">Price</th>
              <th className="px-6 py-3 font-medium">RAM</th>
              <th className="px-6 py-3 font-medium">Storage</th>
              <th className="px-6 py-3 font-medium">CPU</th>
              <th className="px-6 py-3 font-medium">Rating</th>
              <th className="px-6 py-3 font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {data.map((row, idx) => (
              <tr key={idx} className={`transition-colors ${row.isBest ? 'bg-zinc-50/80' : 'hover:bg-zinc-50/50'}`}>
                <td className="px-6 py-4 font-medium text-zinc-900 flex items-center gap-2 text-sm">
                  {row.isBest && <Award className="w-4 h-4 text-zinc-900" />}
                  {row.product}
                </td>
                <td className="px-6 py-4 font-semibold text-zinc-900 text-sm">{row.price}</td>
                <td className="px-6 py-4 text-zinc-600 text-xs">{row.ram}</td>
                <td className="px-6 py-4 text-zinc-600 text-xs">{row.storage}</td>
                <td className="px-6 py-4 text-zinc-600 text-xs">{row.cpu}</td>
                <td className="px-6 py-4 text-zinc-600 text-xs flex items-center gap-1">
                  <Star className="w-3.5 h-3.5 fill-current text-zinc-400" />
                  {row.rating}
                </td>
                <td className="px-6 py-4 font-medium text-zinc-900 text-sm">{row.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
