import type { Exchange } from "../types/orderbook";
import type { AllBalances, AllPositions } from "../types/account";
import { formatNum, capitalize } from "../utils/format";
import { useAccountBalances } from "../hooks/useAccountBalances";
import { useAccountPositions } from "../hooks/useAccountPositions";

interface Props {
  activeExchanges: Exchange[];
}

function BalancesTable({
  exchange,
  currencies,
}: {
  exchange: Exchange;
  currencies: { currency: string; available: number; frozen: number; total: number }[];
}) {
  if (currencies.length === 0) {
    return (
      <div className="py-4 text-center text-white/30 text-sm">No balances</div>
    );
  }

  return (
    <table className="w-full text-xs table-fixed">
      <thead>
        <tr className="text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
          <th className="py-2 px-3 text-left font-medium">Currency</th>
          <th className="py-2 px-3 text-right font-medium">Available</th>
          <th className="py-2 px-3 text-right font-medium">Frozen</th>
          <th className="py-2 px-3 text-right font-medium">Total</th>
        </tr>
      </thead>
      <tbody>
        {currencies.map((c) => (
          <tr
            key={`${exchange}-${c.currency}`}
            className="border-b border-white/5 hover:bg-white/[0.03]"
          >
            <td className="py-2 px-3 font-medium">{c.currency}</td>
            <td className="py-2 px-3 text-right tabular-nums">
              {formatNum(c.available, c.available < 1 ? 6 : 2)}
            </td>
            <td className="py-2 px-3 text-right tabular-nums">
              {formatNum(c.frozen, c.frozen < 1 ? 6 : 2)}
            </td>
            <td className="py-2 px-3 text-right tabular-nums">
              {formatNum(c.total, c.total < 1 ? 6 : 2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PositionsTable({
  exchange,
  positions,
}: {
  exchange: Exchange;
  positions: { currency: string; available: number; frozen: number; total: number }[];
}) {
  if (positions.length === 0) {
    return (
      <div className="py-4 text-center text-white/30 text-sm">
        No positions (non-zero, non-cash)
      </div>
    );
  }

  return (
    <table className="w-full text-xs table-fixed">
      <thead>
        <tr className="text-[10px] uppercase tracking-wider text-white/30 border-b border-white/10">
          <th className="py-2 px-3 text-left font-medium">Currency</th>
          <th className="py-2 px-3 text-right font-medium">Available</th>
          <th className="py-2 px-3 text-right font-medium">Frozen</th>
          <th className="py-2 px-3 text-right font-medium">Total</th>
        </tr>
      </thead>
      <tbody>
        {positions.map((p) => (
          <tr
            key={`${exchange}-${p.currency}`}
            className="border-b border-white/5 hover:bg-white/[0.03]"
          >
            <td className="py-2 px-3 font-medium">{p.currency}</td>
            <td className="py-2 px-3 text-right tabular-nums">
              {formatNum(p.available, p.available < 1 ? 6 : 2)}
            </td>
            <td className="py-2 px-3 text-right tabular-nums">
              {formatNum(p.frozen, p.frozen < 1 ? 6 : 2)}
            </td>
            <td className="py-2 px-3 text-right tabular-nums">
              {formatNum(p.total, p.total < 1 ? 6 : 2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function AccountView({ activeExchanges }: Props) {
  const balancesQuery = useAccountBalances(activeExchanges);
  const positionsQuery = useAccountPositions(activeExchanges);

  const isLoading = balancesQuery.isLoading || positionsQuery.isLoading;
  const refetch = () => {
    balancesQuery.refetch();
    positionsQuery.refetch();
  };

  if (activeExchanges.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-white/30">
        <p className="text-lg mb-2">No exchanges configured</p>
        <p className="text-sm">
          Switch to the Dashboard and add pairs to see account data.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-white/30">
        <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mr-3" />
        Loading account data…
      </div>
    );
  }

  const balancesData: Partial<Record<Exchange, AllBalances>> =
    balancesQuery.data ?? {};
  const positionsData: Partial<Record<Exchange, AllPositions>> =
    positionsQuery.data ?? {};

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <h2 className="text-sm font-semibold text-white/80">
          Balances & Positions
        </h2>
        <button
          onClick={() => refetch()}
          className="text-xs text-white/40 hover:text-white/70 transition-colors border border-white/10 rounded-md px-3 py-1.5 cursor-pointer"
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-auto px-6 py-4 space-y-8">
        {activeExchanges.map((exchange) => (
          <section
            key={exchange}
            className="rounded-lg border border-white/10 bg-white/[0.02] overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-white/10 bg-white/[0.03]">
              <h3 className="text-sm font-semibold text-white">
                {capitalize(exchange)}
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-0 md:gap-0">
              <div className="border-b md:border-b-0 md:border-r border-white/10">
                <div className="px-4 py-2 border-b border-white/10">
                  <span className="text-[10px] uppercase tracking-wider text-white/50">
                    Balances
                  </span>
                </div>
                <div className="p-4">
                  <BalancesTable
                    exchange={exchange}
                    currencies={balancesData[exchange]?.currencies ?? []}
                  />
                </div>
              </div>

              <div>
                <div className="px-4 py-2 border-b border-white/10">
                  <span className="text-[10px] uppercase tracking-wider text-white/50">
                    Positions (non-cash)
                  </span>
                </div>
                <div className="p-4">
                  <PositionsTable
                    exchange={exchange}
                    positions={positionsData[exchange]?.positions ?? []}
                  />
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
