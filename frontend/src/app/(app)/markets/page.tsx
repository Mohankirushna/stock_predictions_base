"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { MarketOverviewStrip } from "@/components/dashboard/market-overview-strip";
import { MoversList } from "@/components/dashboard/movers-list";
import { SectorHeatmap } from "@/components/markets/sector-heatmap";
import { MarketEventsList } from "@/components/markets/market-events-list";
import { getMarketEvents, getMarketOverview, getMovers, getSectorTrends } from "@/lib/api/markets";
import type { MarketEvent, MarketOverview, Mover, SectorTrend } from "@/types/models";

interface MarketsData {
  overview: MarketOverview | null;
  sectors: SectorTrend[];
  gainers: Mover[];
  losers: Mover[];
  events: MarketEvent[];
}

export default function MarketsPage() {
  const [data, setData] = React.useState<MarketsData | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const today = new Date();
    const in30Days = new Date(today.getTime() + 30 * 86_400_000);

    Promise.all([
      getMarketOverview().catch(() => null),
      getSectorTrends().catch(() => []),
      getMovers("gainers", 10).catch(() => []),
      getMovers("losers", 10).catch(() => []),
      getMarketEvents(today.toISOString().slice(0, 10), in30Days.toISOString().slice(0, 10)).catch(() => []),
    ])
      .then(([overview, sectors, gainers, losers, events]) => {
        setData({ overview, sectors, gainers, losers, events });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load markets"));
  }, []);

  return (
    <div>
      <PageHeader title="Markets" description="Sector heat, movers, and the macro calendar." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <MarketOverviewStrip overview={data?.overview ?? null} />

      {data?.overview && (
        <div className="mb-6 rounded-md border border-border bg-panel p-4 text-sm text-muted">
          <p className="mb-2 font-medium text-foreground">{data.overview.narrative}</p>
          <p>{data.overview.outlook}</p>
          {data.overview.risks.length > 0 && (
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-warning">
              {data.overview.risks.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="mb-6">
        <SectorHeatmap sectors={data?.sectors ?? []} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <MoversList title="Top Gainers" movers={data?.gainers ?? []} />
        <MoversList title="Top Losers" movers={data?.losers ?? []} />
        <MarketEventsList events={data?.events ?? []} />
      </div>
    </div>
  );
}
