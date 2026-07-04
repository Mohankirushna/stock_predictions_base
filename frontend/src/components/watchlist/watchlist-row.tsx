"use client";

import Link from "next/link";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChangeBadge } from "@/components/dashboard/change-badge";
import { ScoreGauge } from "@/components/charts/score-gauge";
import { formatCurrency } from "@/lib/utils";
import type { Company, PriceBar, Recommendation } from "@/types/models";

export interface WatchlistRowData {
  symbol: string;
  company: Company | null;
  latestBar: PriceBar | null;
  prevBar: PriceBar | null;
  recommendation: Recommendation | null;
}

export function WatchlistRow({ row, onRemove }: { row: WatchlistRowData; onRemove: () => void }) {
  const price = row.latestBar ? Number(row.latestBar.close) : null;
  const prevClose = row.prevBar ? Number(row.prevBar.close) : null;
  const changePct = price !== null && prevClose ? ((price - prevClose) / prevClose) * 100 : null;

  return (
    <div className="flex items-center justify-between p-3 hover:bg-panel-hover">
      <Link href={`/companies/${row.symbol}`} className="flex min-w-0 items-center gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-panel-hover text-xs font-semibold text-accent">
          {row.symbol.slice(0, 2)}
        </div>
        <div className="min-w-0">
          <p className="font-medium">{row.symbol}</p>
          <p className="truncate text-xs text-muted">{row.company?.name ?? "Unknown company"}</p>
        </div>
      </Link>

      <div className="flex items-center gap-4">
        {row.recommendation && (
          <div className="hidden items-center gap-2 sm:flex">
            <ScoreGauge score={row.recommendation.master_score} size={32} />
            <Badge variant={row.recommendation.action.includes("buy") ? "bull" : row.recommendation.action === "avoid" ? "bear" : "default"}>
              {row.recommendation.action.replace("_", " ")}
            </Badge>
          </div>
        )}
        {price !== null ? (
          <div className="text-right">
            <p className="font-tabular text-sm font-medium">{formatCurrency(price, row.company?.currency)}</p>
            {changePct !== null && <ChangeBadge value={changePct} />}
          </div>
        ) : (
          <p className="text-xs text-muted">No price data</p>
        )}
        <Button variant="ghost" size="icon" onClick={onRemove} aria-label={`Remove ${row.symbol}`}>
          <X className="size-4" />
        </Button>
      </div>
    </div>
  );
}
