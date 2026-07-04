"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { MarketOverviewStrip } from "@/components/dashboard/market-overview-strip";
import { OpportunityCard } from "@/components/dashboard/opportunity-card";
import { NewsFeed } from "@/components/dashboard/news-feed";
import { MoversList } from "@/components/dashboard/movers-list";
import { EarningsList } from "@/components/dashboard/earnings-list";
import { ScoreRankedList } from "@/components/dashboard/score-ranked-list";
import { getMarketEvents, getMarketOverview, getMovers } from "@/lib/api/markets";
import { getTrendingNews } from "@/lib/api/news";
import { listOpportunities, screenRecommendations } from "@/lib/api/research";
import type { MarketEvent, MarketOverview, Mover, NewsItem, Opportunity, Recommendation } from "@/types/models";

interface DashboardData {
  overview: MarketOverview | null;
  opportunities: Opportunity[];
  news: NewsItem[];
  gainers: Mover[];
  losers: Mover[];
  events: MarketEvent[];
  bullish: Recommendation[];
  bearish: Recommendation[];
}

export default function DashboardPage() {
  const [data, setData] = React.useState<DashboardData | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const today = new Date();
    const in30Days = new Date(today.getTime() + 30 * 86_400_000);

    Promise.all([
      getMarketOverview().catch(() => null),
      listOpportunities().catch(() => []),
      getTrendingNews(15).catch(() => []),
      getMovers("gainers", 6).catch(() => []),
      getMovers("losers", 6).catch(() => []),
      getMarketEvents(today.toISOString().slice(0, 10), in30Days.toISOString().slice(0, 10)).catch(() => []),
      screenRecommendations({ minScore: 65 }).catch(() => ({ data: [] as Recommendation[] })),
      screenRecommendations({ minScore: 0 }).catch(() => ({ data: [] as Recommendation[] })),
    ]).then(([overview, opportunities, news, gainers, losers, events, bullishRes, allRes]) => {
      // "Most bearish" = lowest scores among the active screener results —
      // the backend only supports a minimum-score filter, so this sorts
      // client-side rather than adding a max-score query param for one card.
      const bearish = [...allRes.data].sort((a, b) => a.master_score - b.master_score).slice(0, 6);
      setData({
        overview, opportunities, news, gainers, losers, events,
        bullish: bullishRes.data.slice(0, 6), bearish,
      });
    }).catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, []);

  return (
    <div>
      <PageHeader title="Dashboard" description="Market overview, AI opportunities, and today's movers." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <MarketOverviewStrip overview={data?.overview ?? null} />

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-muted">AI Opportunities</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {(data?.opportunities ?? []).length === 0 && (
              <p className="text-sm text-muted">No opportunities discovered yet.</p>
            )}
            {data?.opportunities.map((o) => (
              <OpportunityCard key={o.symbol} opportunity={o} />
            ))}
          </div>
        </div>
        <NewsFeed items={data?.news ?? []} />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <MoversList title="Top Gainers" movers={data?.gainers ?? []} />
        <MoversList title="Top Losers" movers={data?.losers ?? []} />
        <EarningsList events={data?.events ?? []} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ScoreRankedList title="Most Bullish" items={data?.bullish ?? []} />
        <ScoreRankedList title="Most Bearish" items={data?.bearish ?? []} />
      </div>
    </div>
  );
}
