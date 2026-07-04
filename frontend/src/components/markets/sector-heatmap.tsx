import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SectorTrend } from "@/types/models";

const TREND_STYLE: Record<string, string> = {
  strong_up: "bg-bull/25 border-bull/40 text-bull",
  up: "bg-bull/10 border-bull/30 text-bull",
  neutral: "bg-panel-hover border-border text-muted",
  down: "bg-bear/10 border-bear/30 text-bear",
  strong_down: "bg-bear/25 border-bear/40 text-bear",
};

export function SectorHeatmap({ sectors }: { sectors: SectorTrend[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sector Trends</CardTitle>
      </CardHeader>
      <CardContent>
        {sectors.length === 0 ? (
          <p className="text-sm text-muted">No sector data yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {sectors.map((s) => (
              <div
                key={s.sector}
                className={`rounded-md border p-3 text-center text-sm font-medium ${TREND_STYLE[s.trend] ?? TREND_STYLE.neutral}`}
              >
                <p className="truncate">{s.sector}</p>
                <p className="mt-1 text-[11px] capitalize opacity-80">{s.trend.replace("_", " ")}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
