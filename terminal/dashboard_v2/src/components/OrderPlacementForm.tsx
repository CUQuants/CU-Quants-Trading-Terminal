import { useState } from "react";
import type { Exchange } from "../types/orderbook";
import { usePlaceOrder } from "../hooks/usePlaceOrder";

interface Props {
  exchange: Exchange;
  pair: string;
}

export function OrderPlacementForm({ exchange, pair }: Props) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [type, setType] = useState<"limit" | "market">("limit");
  const [price, setPrice] = useState("");
  const [size, setSize] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mutation = usePlaceOrder(exchange);

  function validate(): boolean {
    const e: Record<string, string> = {};
    const sizeNum = parseFloat(size);

    if (!size || isNaN(sizeNum) || sizeNum <= 0) {
      e.size = "Size must be a positive number";
    }

    if (type === "limit") {
      const priceNum = parseFloat(price);
      if (!price || isNaN(priceNum) || priceNum <= 0) {
        e.price = "Price must be a positive number";
      }
    }

    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (!validate()) return;

    mutation.mutate({
      pair,
      side,
      type,
      price: type === "limit" ? parseFloat(price) : undefined,
      size: parseFloat(size),
    });
  }

  const isBuy = side === "buy";

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 p-4">
      {/* Side toggle */}
      <div className="flex rounded-lg overflow-hidden border border-white/10">
        <button
          type="button"
          onClick={() => setSide("buy")}
          className={`flex-1 py-2 text-sm font-medium transition-colors cursor-pointer ${
            isBuy
              ? "bg-green-600 text-white"
              : "bg-transparent text-white/40 hover:text-white/60"
          }`}
        >
          Buy
        </button>
        <button
          type="button"
          onClick={() => setSide("sell")}
          className={`flex-1 py-2 text-sm font-medium transition-colors cursor-pointer ${
            !isBuy
              ? "bg-red-600 text-white"
              : "bg-transparent text-white/40 hover:text-white/60"
          }`}
        >
          Sell
        </button>
      </div>

      {/* Type */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setType("limit")}
          className={`flex-1 py-1.5 text-xs rounded border transition-colors cursor-pointer ${
            type === "limit"
              ? "border-blue-500 text-blue-400 bg-blue-500/10"
              : "border-white/10 text-white/40 hover:border-white/20"
          }`}
        >
          Limit
        </button>
        <button
          type="button"
          onClick={() => setType("market")}
          className={`flex-1 py-1.5 text-xs rounded border transition-colors cursor-pointer ${
            type === "market"
              ? "border-blue-500 text-blue-400 bg-blue-500/10"
              : "border-white/10 text-white/40 hover:border-white/20"
          }`}
        >
          Market
        </button>
      </div>

      {/* Price (limit only) */}
      {type === "limit" && (
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-white/40 mb-1">
            Price
          </label>
          <input
            type="number"
            step="any"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="0.00"
            className="w-full px-3 py-2 text-sm rounded-lg border border-white/10 bg-white/5 text-white outline-none focus:border-blue-500"
          />
          {errors.price && (
            <p className="text-red-400 text-xs mt-1">{errors.price}</p>
          )}
        </div>
      )}

      {/* Size */}
      <div>
        <label className="block text-[10px] uppercase tracking-wider text-white/40 mb-1">
          Size
        </label>
        <input
          type="number"
          step="any"
          value={size}
          onChange={(e) => setSize(e.target.value)}
          placeholder="0.00"
          className="w-full px-3 py-2 text-sm rounded-lg border border-white/10 bg-white/5 text-white outline-none focus:border-blue-500"
        />
        {errors.size && (
          <p className="text-red-400 text-xs mt-1">{errors.size}</p>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={mutation.isPending}
        className={`w-full py-2.5 text-sm font-semibold rounded-lg transition-colors cursor-pointer disabled:opacity-50 ${
          isBuy
            ? "bg-green-600 hover:bg-green-500 text-white"
            : "bg-red-600 hover:bg-red-500 text-white"
        }`}
      >
        {mutation.isPending
          ? "Submitting..."
          : `${side === "buy" ? "Buy" : "Sell"} ${pair}`}
      </button>
    </form>
  );
}
