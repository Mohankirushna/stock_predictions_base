"use client";

import * as React from "react";
import { useParams } from "next/navigation";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CandlestickChart } from "@/components/charts/candlestick-chart";
import { VolumePane, RsiPane } from "@/components/charts/indicator-panes";
import { CompanyHeader } from "@/components/company/company-header";
import { RecommendationCard } from "@/components/company/recommendation-card";
import { NewsTab } from "@/components/company/news-tab";
import { TechnicalsTab } from "@/components/company/technicals-tab";
import { FundamentalsTab } from "@/components/company/fundamentals-tab";
import { ResearchTab } from "@/components/company/research-tab";
import { CompetitorsTab } from "@/components/company/competitors-tab";
import { PredictionsTab } from "@/components/company/predictions-tab";
import { CreateAlertDialog } from "@/components/company/create-alert-dialog";
import {
  getCompany,
  getCompanyNews,
  getCompanyPredictions,
  getCompanyRecommendation,
  getCompanyResearch,
  getCompetitors,
  getFundamentals,
  getPrices,
  getTechnicals,
  trackCompany,
} from "@/lib/api/companies";
import { ApiRequestError } from "@/lib/api/client";
import { generateReport, getTaskStatus } from "@/lib/api/research";
import { addWatchlistItem, listWatchlists, removeWatchlistItem } from "@/lib/api/watchlists";
import { createAlert } from "@/lib/api/alerts";
import type {
  AlertType,
  Company,
  Fundamentals,
  NewsItem,
  Prediction,
  PriceBar,
  Recommendation,
  ResearchReport,
  Technicals,
  Watchlist,
} from "@/types/models";

interface CompanyData {
  company: Company;
  prices: PriceBar[];
  technicals: Technicals | null;
  fundamentals: Fundamentals[] | null;
  news: NewsItem[];
  research: ResearchReport | null;
  recommendation: Recommendation | null;
  predictions: Prediction[];
  competitors: Company[];
}

export default function CompanyPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = (params.symbol ?? "").toUpperCase();

  const [data, setData] = React.useState<CompanyData | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [notTracked, setNotTracked] = React.useState(false);
  const [tracking, setTracking] = React.useState(false);
  const [watchlists, setWatchlists] = React.useState<Watchlist[]>([]);
  const [generating, setGenerating] = React.useState(false);
  const [alertDialogOpen, setAlertDialogOpen] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);

  const loadData = React.useCallback(() => {
    Promise.all([
      getCompany(symbol),
      getPrices(symbol),
      getTechnicals(symbol),
      getFundamentals(symbol),
      getCompanyNews(symbol).catch(() => ({ data: [] as NewsItem[] })),
      getCompanyResearch(symbol),
      getCompanyRecommendation(symbol),
      getCompanyPredictions(symbol).catch(() => []),
      getCompetitors(symbol).catch(() => []),
      listWatchlists().catch(() => []),
    ])
      .then(([company, prices, technicals, fundamentals, newsRes, research, recommendation, predictions, competitors, wl]) => {
        setData({
          company, prices, technicals, fundamentals,
          news: newsRes.data, research, recommendation, predictions, competitors,
        });
        setWatchlists(wl);
        setError(null);
        setNotTracked(false);
      })
      .catch((err) => {
        if (err instanceof ApiRequestError && err.status === 404) {
          setNotTracked(true);
          setError(null);
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load company");
        setNotTracked(false);
      });
  }, [symbol]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleTrack() {
    setTracking(true);
    setError(null);
    try {
      await trackCompany(symbol);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Couldn't fetch real data for ${symbol}`);
    } finally {
      setTracking(false);
    }
  }

  const defaultWatchlist = watchlists[0] ?? null;
  const inWatchlist = !!defaultWatchlist?.symbols.includes(symbol);

  async function handleToggleWatchlist() {
    if (!defaultWatchlist) {
      setMessage("Create a watchlist first from the Watchlist page.");
      return;
    }
    if (inWatchlist) {
      await removeWatchlistItem(defaultWatchlist.id, symbol);
      setWatchlists((prev) =>
        prev.map((w) => (w.id === defaultWatchlist.id ? { ...w, symbols: w.symbols.filter((s) => s !== symbol) } : w))
      );
    } else {
      const updated = await addWatchlistItem(defaultWatchlist.id, symbol);
      setWatchlists((prev) => prev.map((w) => (w.id === defaultWatchlist.id ? updated : w)));
    }
  }

  async function handleCreateAlert(alertType: AlertType) {
    await createAlert({ symbol, alert_type: alertType });
    setMessage(`Alert created for ${symbol}.`);
  }

  async function handleGenerateReport() {
    setGenerating(true);
    try {
      const { task_id } = await generateReport(symbol);
      const poll = async (attempt = 0): Promise<void> => {
        if (attempt > 20) return;
        const status = await getTaskStatus(task_id);
        if (status.status === "SUCCESS") {
          const research = await getCompanyResearch(symbol);
          setData((prev) => (prev ? { ...prev, research } : prev));
          return;
        }
        if (status.status === "FAILURE") return;
        await new Promise((r) => setTimeout(r, 1500));
        await poll(attempt + 1);
      };
      await poll();
    } finally {
      setGenerating(false);
    }
  }

  if (notTracked) {
    return (
      <div>
        <PageHeader title={symbol} description="Chart, AI recommendation, and research." />
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
            <p className="text-sm text-muted">
              {symbol} isn&rsquo;t tracked yet. Fetch real quotes, price history, and an AI
              recommendation for it from Yahoo Finance?
            </p>
            {error && <p className="text-sm text-bear">{error}</p>}
            <Button onClick={() => void handleTrack()} disabled={tracking}>
              {tracking ? "Fetching real data…" : "Track this stock"}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title={symbol} description="Chart, AI recommendation, and research." />
        <p className="text-sm text-bear">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title={symbol} description="Chart, AI recommendation, and research." />
        <p className="text-sm text-muted">Loading…</p>
      </div>
    );
  }

  const rec = data.recommendation;
  const latestBar = data.prices.at(-1) ?? null;
  const prevBar = data.prices.at(-2) ?? null;

  return (
    <div>
      <CompanyHeader
        company={data.company}
        latestBar={latestBar}
        prevClose={prevBar ? Number(prevBar.close) : null}
        onAddToWatchlist={() => void handleToggleWatchlist()}
        onCreateAlert={() => setAlertDialogOpen(true)}
        inWatchlist={inWatchlist}
      />

      {message && <p className="mb-4 text-sm text-accent">{message}</p>}

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-4">
              <CandlestickChart
                bars={data.prices}
                technicals={data.technicals}
                entryLow={rec ? Number(rec.entry_zone_low) : undefined}
                entryHigh={rec ? Number(rec.entry_zone_high) : undefined}
                stopLoss={rec ? Number(rec.stop_loss) : undefined}
                takeProfits={rec ? [Number(rec.take_profit_1), Number(rec.take_profit_2), Number(rec.take_profit_3)] : undefined}
              />
              <div className="mt-2 grid grid-cols-1 gap-3 border-t border-border pt-3 sm:grid-cols-2">
                <VolumePane bars={data.prices} />
                <RsiPane value={data.technicals ? Number(data.technicals.rsi_14) : null} />
              </div>
            </CardContent>
          </Card>
        </div>
        <RecommendationCard recommendation={rec} currency={data.company.currency} />
      </div>

      <Tabs defaultValue="news">
        <TabsList>
          <TabsTrigger value="news">News</TabsTrigger>
          <TabsTrigger value="technicals">Technicals</TabsTrigger>
          <TabsTrigger value="fundamentals">Financials</TabsTrigger>
          <TabsTrigger value="research">AI Research</TabsTrigger>
          <TabsTrigger value="competitors">Competitors</TabsTrigger>
          <TabsTrigger value="predictions">Predictions</TabsTrigger>
        </TabsList>
        <TabsContent value="news">
          <NewsTab items={data.news} />
        </TabsContent>
        <TabsContent value="technicals">
          <TechnicalsTab technicals={data.technicals} />
        </TabsContent>
        <TabsContent value="fundamentals">
          <FundamentalsTab snapshots={data.fundamentals} />
        </TabsContent>
        <TabsContent value="research">
          <ResearchTab report={data.research} onGenerate={() => void handleGenerateReport()} generating={generating} />
        </TabsContent>
        <TabsContent value="competitors">
          <CompetitorsTab competitors={data.competitors} />
        </TabsContent>
        <TabsContent value="predictions">
          <PredictionsTab predictions={data.predictions} />
        </TabsContent>
      </Tabs>

      <CreateAlertDialog
        symbol={symbol}
        open={alertDialogOpen}
        onOpenChange={setAlertDialogOpen}
        onCreate={handleCreateAlert}
      />
    </div>
  );
}
