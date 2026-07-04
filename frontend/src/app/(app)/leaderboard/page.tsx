"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { getLeaderboard } from "@/lib/api/predictions";
import type { LeaderboardEntry } from "@/types/models";

const HORIZON_ORDER = ["1d", "7d", "30d", "90d"];

function accuracyColor(pct: number): string {
  if (pct >= 65) return "text-bull";
  if (pct <= 40) return "text-bear";
  return "text-warning";
}

export default function LeaderboardPage() {
  const [entries, setEntries] = React.useState<LeaderboardEntry[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    getLeaderboard()
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load leaderboard"));
  }, []);

  const bySector = React.useMemo(() => {
    const map = new Map<string, Map<string, LeaderboardEntry>>();
    for (const e of entries ?? []) {
      if (!map.has(e.sector)) map.set(e.sector, new Map());
      map.get(e.sector)!.set(e.horizon, e);
    }
    return map;
  }, [entries]);

  const horizons = React.useMemo(() => {
    const set = new Set<string>();
    for (const e of entries ?? []) set.add(e.horizon);
    return HORIZON_ORDER.filter((h) => set.has(h)).concat([...set].filter((h) => !HORIZON_ORDER.includes(h)));
  }, [entries]);

  return (
    <div>
      <PageHeader title="Leaderboard" description="Prediction accuracy by sector, horizon, and AI provider." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      {entries === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : entries.length === 0 ? (
        <Card className="p-4 text-sm text-muted">
          No prediction accuracy data yet — the Learning Agent hasn&rsquo;t scored enough resolved predictions.
        </Card>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted">
                <th className="p-3 font-medium">Sector</th>
                {horizons.map((h) => (
                  <th key={h} className="p-3 text-right font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[...bySector.entries()].map(([sector, byHorizon]) => (
                <tr key={sector} className="hover:bg-panel-hover">
                  <td className="p-3 font-medium">{sector}</td>
                  {horizons.map((h) => {
                    const entry = byHorizon.get(h);
                    return (
                      <td key={h} className="p-3 text-right">
                        {entry ? (
                          <div>
                            <span className={`font-tabular font-semibold ${accuracyColor(entry.rolling_accuracy * 100)}`}>
                              {(entry.rolling_accuracy * 100).toFixed(1)}%
                            </span>
                            <p className="text-[11px] text-muted">n={entry.sample_size}</p>
                          </div>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
