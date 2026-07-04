"use client";

import * as React from "react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PredictionsTab } from "@/components/company/predictions-tab";
import { getCompanyPredictions } from "@/lib/api/companies";
import type { Prediction } from "@/types/models";

export default function PredictionsPage() {
  const [symbol, setSymbol] = React.useState("");
  const [lookedUp, setLookedUp] = React.useState<string | null>(null);
  const [predictions, setPredictions] = React.useState<Prediction[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    const s = symbol.trim().toUpperCase();
    if (!s) return;
    setError(null);
    setPredictions(null);
    getCompanyPredictions(s)
      .then((preds) => {
        setPredictions(preds);
        setLookedUp(s);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load predictions"));
  }

  return (
    <div>
      <PageHeader title="Predictions" description="Past calls, outcomes, and calibration." />

      <Card className="mb-6 p-4 text-sm text-muted">
        Want aggregate accuracy by sector and horizon instead?{" "}
        <Link href="/leaderboard" className="text-accent hover:underline">
          View the Leaderboard
        </Link>
        .
      </Card>

      <form onSubmit={handleLookup} className="mb-6 flex gap-2">
        <Input
          placeholder="Look up a symbol (e.g. AAPL)…"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit">Search</Button>
      </form>

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      {lookedUp && predictions !== null && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-muted">
            Prediction history for{" "}
            <Link href={`/companies/${lookedUp}`} className="text-accent hover:underline">
              {lookedUp}
            </Link>
          </h2>
          <PredictionsTab predictions={predictions} />
        </div>
      )}

      {!lookedUp && <p className="text-sm text-muted">Search a symbol above to see its prediction history.</p>}
    </div>
  );
}
