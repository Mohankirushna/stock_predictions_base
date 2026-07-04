import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreGauge } from "@/components/charts/score-gauge";
import { Badge } from "@/components/ui/badge";
import type { Recommendation } from "@/types/models";

export function ScoreRankedList({ title, items }: { title: string; items: Recommendation[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.length === 0 && <p className="text-sm text-muted">No active recommendations yet.</p>}
        {items.map((rec) => (
          <Link
            key={rec.id}
            href={`/companies/${rec.symbol}`}
            className="flex items-center justify-between rounded-md p-1.5 -mx-1.5 hover:bg-panel-hover"
          >
            <div className="flex items-center gap-2">
              <ScoreGauge score={rec.master_score} size={36} />
              <span className="font-medium">{rec.symbol}</span>
            </div>
            <Badge variant={rec.action.includes("buy") ? "bull" : rec.action === "avoid" ? "bear" : "default"}>
              {rec.action.replace("_", " ")}
            </Badge>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
