import Link from "next/link";

import { Card } from "@/components/ui/card";
import { ChangeBadge } from "@/components/dashboard/change-badge";
import { formatCurrency } from "@/lib/utils";
import type { PortfolioHolding } from "@/types/models";

export function HoldingsTable({ holdings, currency }: { holdings: PortfolioHolding[]; currency: string }) {
  if (holdings.length === 0) {
    return <Card className="p-4 text-sm text-muted">No holdings yet — record a transaction to get started.</Card>;
  }

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted">
            <th className="p-3 font-medium">Symbol</th>
            <th className="p-3 font-medium">Sector</th>
            <th className="p-3 text-right font-medium">Quantity</th>
            <th className="p-3 text-right font-medium">Avg Cost</th>
            <th className="p-3 text-right font-medium">Price</th>
            <th className="p-3 text-right font-medium">Market Value</th>
            <th className="p-3 text-right font-medium">Unrealized P&amp;L</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {holdings.map((h) => (
            <tr key={h.symbol} className="hover:bg-panel-hover">
              <td className="p-3">
                <Link href={`/companies/${h.symbol}`} className="font-medium hover:text-accent">
                  {h.symbol}
                </Link>
              </td>
              <td className="p-3 text-muted">{h.sector}</td>
              <td className="p-3 text-right font-tabular">{h.quantity}</td>
              <td className="p-3 text-right font-tabular">{formatCurrency(h.avg_cost, currency)}</td>
              <td className="p-3 text-right font-tabular">{formatCurrency(h.price, currency)}</td>
              <td className="p-3 text-right font-tabular">{formatCurrency(h.market_value, currency)}</td>
              <td className="p-3 text-right">
                <div className="flex flex-col items-end">
                  <span className={`font-tabular ${Number(h.unrealized_pnl) >= 0 ? "text-bull" : "text-bear"}`}>
                    {formatCurrency(h.unrealized_pnl, currency)}
                  </span>
                  <ChangeBadge value={h.unrealized_pnl_pct} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
