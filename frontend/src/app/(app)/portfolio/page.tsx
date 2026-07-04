"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { AllocationChart } from "@/components/portfolio/allocation-chart";
import { RecordTransactionDialog } from "@/components/portfolio/record-transaction-dialog";
import {
  createPortfolio,
  getPortfolioAnalytics,
  listPortfolios,
  recordTransaction,
} from "@/lib/api/portfolios";
import { formatCurrency } from "@/lib/utils";
import type { Portfolio, PortfolioAnalytics } from "@/types/models";

const GRADE_VARIANT: Record<string, "bull" | "bear" | "warning" | "default"> = {
  A: "bull",
  B: "bull",
  C: "warning",
  D: "bear",
  F: "bear",
};

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = React.useState<Portfolio[]>([]);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [analytics, setAnalytics] = React.useState<PortfolioAnalytics | null>(null);
  const [newName, setNewName] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [txDialogOpen, setTxDialogOpen] = React.useState(false);

  React.useEffect(() => {
    listPortfolios()
      .then((list) => {
        setPortfolios(list);
        setActiveId((prev) => prev ?? list[0]?.id ?? null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load portfolios"));
  }, []);

  const active = portfolios.find((p) => p.id === activeId) ?? null;

  React.useEffect(() => {
    if (!active) return;
    getPortfolioAnalytics(active.id)
      .then(setAnalytics)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load analytics"));
  }, [active]);

  async function handleCreatePortfolio() {
    if (!newName.trim()) return;
    const p = await createPortfolio(newName.trim());
    setPortfolios((prev) => [...prev, p]);
    setActiveId(p.id);
    setNewName("");
  }

  async function handleRecordTransaction(input: {
    symbol: string;
    side: "buy" | "sell";
    quantity: string;
    price: string;
    fees?: string;
    note?: string;
  }) {
    if (!active) return;
    const updated = await recordTransaction(active.id, input);
    setPortfolios((prev) => prev.map((p) => (p.id === active.id ? updated : p)));
    const refreshed = await getPortfolioAnalytics(active.id);
    setAnalytics(refreshed);
  }

  return (
    <div>
      <PageHeader title="Portfolio" description="Holdings, P&L, allocation, and rebalancing suggestions." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {portfolios.map((p) => (
          <button
            key={p.id}
            onClick={() => setActiveId(p.id)}
            className={`rounded-md border px-3 py-1.5 text-sm ${
              p.id === activeId ? "border-accent bg-accent/10 text-accent" : "border-border text-muted hover:bg-panel-hover"
            }`}
          >
            {p.name}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <Input
            placeholder="New portfolio name…"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="h-9 w-48"
          />
          <Button size="sm" onClick={() => void handleCreatePortfolio()}>
            Create
          </Button>
        </div>
      </div>

      {portfolios.length === 0 ? (
        <Card className="p-4 text-sm text-muted">You don&rsquo;t have any portfolios yet. Create one above.</Card>
      ) : active ? (
        <>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-muted">
              {active.name} &middot; {active.transaction_count} transactions &middot; {formatCurrency(active.cash_balance, active.base_currency)} cash
            </p>
            <Button size="sm" onClick={() => setTxDialogOpen(true)}>
              Record Transaction
            </Button>
          </div>

          {analytics && (
            <>
              <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <Card className="p-3">
                  <p className="text-[11px] text-muted">Total Value</p>
                  <p className="font-tabular text-lg font-semibold">
                    {formatCurrency(analytics.total_value, active.base_currency)}
                  </p>
                </Card>
                <Card className="p-3">
                  <p className="text-[11px] text-muted">Cash</p>
                  <p className="font-tabular text-lg font-semibold">
                    {formatCurrency(analytics.cash_balance, active.base_currency)}
                  </p>
                </Card>
                <Card className="p-3">
                  <p className="text-[11px] text-muted">Unrealized P&amp;L</p>
                  <p className={`font-tabular text-lg font-semibold ${Number(analytics.unrealized_pnl) >= 0 ? "text-bull" : "text-bear"}`}>
                    {formatCurrency(analytics.unrealized_pnl, active.base_currency)}
                  </p>
                  <p className={`text-xs ${analytics.unrealized_pnl_pct >= 0 ? "text-bull" : "text-bear"}`}>
                    {analytics.unrealized_pnl_pct >= 0 ? "+" : ""}
                    {analytics.unrealized_pnl_pct.toFixed(2)}%
                  </p>
                </Card>
                <Card className="p-3">
                  <p className="text-[11px] text-muted">Health Grade</p>
                  <Badge variant={GRADE_VARIANT[analytics.health_grade] ?? "default"} className="mt-1 text-base">
                    {analytics.health_grade}
                  </Badge>
                </Card>
                <Card className="p-3">
                  <p className="text-[11px] text-muted">Diversification</p>
                  <p className="font-tabular text-lg font-semibold">{Math.round(analytics.diversification_score)}</p>
                </Card>
                <Card className="p-3">
                  <p className="text-[11px] text-muted">Risk Score</p>
                  <p className="font-tabular text-lg font-semibold">{Math.round(analytics.risk_score)}</p>
                </Card>
              </div>

              <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
                <AllocationChart title="Allocation by Symbol" breakdown={analytics.allocation_pct} />
                <AllocationChart title="Sector Exposure" breakdown={analytics.sector_exposure_pct} />
              </div>

              {analytics.rebalancing_suggestions.length > 0 && (
                <Card className="mb-6 p-4">
                  <h3 className="mb-2 text-sm font-medium">Rebalancing Suggestions</h3>
                  <ul className="list-disc space-y-1 pl-4 text-sm text-muted">
                    {analytics.rebalancing_suggestions.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </Card>
              )}

              <HoldingsTable holdings={analytics.holdings} currency={active.base_currency} />
            </>
          )}
        </>
      ) : null}

      <RecordTransactionDialog
        open={txDialogOpen}
        onOpenChange={setTxDialogOpen}
        onSubmit={handleRecordTransaction}
      />
    </div>
  );
}
