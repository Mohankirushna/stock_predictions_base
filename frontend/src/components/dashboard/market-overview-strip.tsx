import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { MarketOverview } from "@/types/models";

const TREND_VARIANT: Record<string, "bull" | "bear" | "default"> = {
  strong_up: "bull",
  up: "bull",
  neutral: "default",
  down: "bear",
  strong_down: "bear",
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-4">
      <span className="text-[11px] uppercase tracking-wide text-muted">{label}</span>
      <span className="font-tabular text-sm font-medium">{value}</span>
    </div>
  );
}

export function MarketOverviewStrip({ overview }: { overview: MarketOverview | null }) {
  if (!overview) {
    return (
      <Card className="mb-6 p-4 text-sm text-muted">
        Market overview isn&rsquo;t available yet — the Market Intelligence Agent hasn&rsquo;t run.
      </Card>
    );
  }

  return (
    <Card className="mb-6 flex flex-wrap items-center divide-x divide-border py-3">
      <div className="px-4">
        <Badge variant={TREND_VARIANT[overview.market_trend] ?? "default"}>
          {overview.market_trend.replace("_", " ")}
        </Badge>
      </div>
      <Stat label="Fear & Greed" value={`${overview.fear_greed}/100`} />
      <Stat label="VIX" value={overview.vix?.toFixed(1) ?? "—"} />
      <Stat label="Oil" value={overview.oil ? `$${overview.oil.toFixed(2)}` : "—"} />
      <Stat label="Gold" value={overview.gold ? `$${overview.gold.toFixed(2)}` : "—"} />
      <Stat label="BTC" value={overview.btc ? `$${overview.btc.toLocaleString()}` : "—"} />
    </Card>
  );
}
