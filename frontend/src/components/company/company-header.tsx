"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import type { Company, PriceBar } from "@/types/models";

export function CompanyHeader({
  company,
  latestBar,
  prevClose,
  onAddToWatchlist,
  onCreateAlert,
  inWatchlist,
}: {
  company: Company;
  latestBar: PriceBar | null;
  prevClose: number | null;
  onAddToWatchlist: () => void;
  onCreateAlert: () => void;
  inWatchlist: boolean;
}) {
  const price = latestBar ? Number(latestBar.close) : null;
  const change = price !== null && prevClose ? price - prevClose : null;
  const changePct = price !== null && prevClose ? (change! / prevClose) * 100 : null;
  const positive = (change ?? 0) >= 0;

  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-panel-hover text-lg font-bold text-accent">
          {company.symbol.slice(0, 2)}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold">{company.symbol}</h1>
            <Badge variant="outline">{company.exchange}</Badge>
            <Badge variant="default">{company.sector}</Badge>
          </div>
          <p className="text-sm text-muted">{company.name}</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {price !== null && (
          <div className="text-right">
            <p className="font-mono text-2xl font-semibold">{formatCurrency(price, company.currency)}</p>
            {change !== null && changePct !== null && (
              <p className={`text-sm font-medium ${positive ? "text-bull" : "text-bear"}`}>
                {positive ? "+" : ""}
                {change.toFixed(2)} ({positive ? "+" : ""}
                {changePct.toFixed(2)}%)
              </p>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <Button variant={inWatchlist ? "subtle" : "outline"} size="sm" onClick={onAddToWatchlist}>
            {inWatchlist ? "In Watchlist" : "+ Watchlist"}
          </Button>
          <Button variant="outline" size="sm" onClick={onCreateAlert}>
            Alert
          </Button>
        </div>
      </div>
    </div>
  );
}
