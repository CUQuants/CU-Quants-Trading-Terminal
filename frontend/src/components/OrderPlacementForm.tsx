import { useState, useEffect } from "react";
import type { Exchange } from "../types/orderbook";
import { usePlaceOrder } from "../hooks/usePlaceOrder";
import { useAvailableCash } from "../hooks/useAvailableCash";
import { useAvailablePositions } from "../hooks/useAvailablePositions";
import { formatNum } from "../utils/format";

interface Props {
  exchange: Exchange;
  pair: string;
}

export function OrderPlacementForm({ exchange, pair }: Props) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [type, setType] = useState<"limit" | "market" | "iceberg">("limit");
  const [price, setPrice] = useState("");
  const [size, setSize] = useState("");
  const [visibleSize, setVisibleSize] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (type === "iceberg" && exchange !== "kraken") {
      setType("limit");
      setVisibleSize("");
    }
  }, [exchange, type]);

  const mutation = usePlaceOrder(exchange);
  const cashQuery = useAvailableCash(exchange, pair);
  const positionsQuery = useAvailablePositions(exchange, pair);

  function validate(): boolean {
    const e: Record<string, string> = {};
    const sizeNum = parseFloat(size);

    if (!size || isNaN(sizeNum) || sizeNum <= 0) {
      e.size = "Size must be a positive number";
    }

    if (type === "limit" || type === "iceberg") {
      const priceNum = parseFloat(price);
      if (!price || isNaN(priceNum) || priceNum <= 0) {
        e.price = "Price must be a positive number";
      }
    }

    if (type === "iceberg") {
      const visNum = parseFloat(visibleSize);
      if (!visibleSize || isNaN(visNum) || visNum <= 0) {
        e.visibleSize = "Display size must be a positive number";
      } else if (!isNaN(sizeNum) && visNum > sizeNum) {
        e.visibleSize = "Display size cannot exceed total size";
      } else if (!isNaN(sizeNum) && visNum < sizeNum / 15) {
        e.visibleSize = "Display size must be at least 1/15 of total size";
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
      price: type === "limit" || type === "iceberg" ? parseFloat(price) : undefined,
      visible_size: type === "iceberg" ? parseFloat(visibleSize) : undefined,
      size: parseFloat(size),
    });
  }

  const isBuy = side === "buy";

  const availableDisplay = isBuy ? (
    cashQuery.isLoading ? (
      <span className="text-white/40 text-sm">Loading cash…</span>
    ) : cashQuery.isError ? (
      <span className="text-red-400 text-sm">Failed to load cash</span>
    ) : cashQuery.data ? (
      <span className="text-white/70 text-sm">
        Available: {formatNum(cashQuery.data.available, 2)}{" "}
        {cashQuery.data.currency}
      </span>
    ) : null
  ) : positionsQuery.isLoading ? (
    <span className="text-white/40 text-sm">Loading position…</span>
  ) : positionsQuery.isError ? (
    <span className="text-red-400 text-sm">Failed to load position</span>
  ) : positionsQuery.data ? (
    <span className="text-white/70 text-sm">
      Available: {formatNum(positionsQuery.data.available, 6)}{" "}
      {positionsQuery.data.base_currency}
    </span>
  ) : null;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 p-4">
      {/* Available balance */}
      {availableDisplay && (
        <div className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2">
          {availableDisplay}
        </div>
      )}

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
        {exchange === "kraken" && (
          <button
            type="button"
            onClick={() => setType("iceberg")}
            className={`flex-1 py-1.5 text-xs rounded border transition-colors cursor-pointer ${
              type === "iceberg"
                ? "border-blue-500 text-blue-400 bg-blue-500/10"
                : "border-white/10 text-white/40 hover:border-white/20"
            }`}
          >
            Iceberg
          </button>
        )}
      </div>

      {/* Price (limit & iceberg) */}
      {(type === "limit" || type === "iceberg") && (
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

      {/* Display size (iceberg only) */}
      {type === "iceberg" && (
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-white/40 mb-1">
            Display Size
          </label>
          <input
            type="number"
            step="any"
            value={visibleSize}
            onChange={(e) => setVisibleSize(e.target.value)}
            placeholder="Visible quantity in book"
            className="w-full px-3 py-2 text-sm rounded-lg border border-white/10 bg-white/5 text-white outline-none focus:border-blue-500"
          />
          <p className="text-white/30 text-[10px] mt-1">Min 1/15 of total size</p>
          {errors.visibleSize && (
            <p className="text-red-400 text-xs mt-1">{errors.visibleSize}</p>
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
