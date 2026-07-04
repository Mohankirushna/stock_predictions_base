"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreGauge } from "@/components/charts/score-gauge";
import { formatCurrency } from "@/lib/utils";
import type { Recommendation, ScoreBreakdown } from "@/types/models";

const BREAKDOWN_LABELS: Record<keyof ScoreBreakdown, string> = {
  news: "News",
  technicals: "Technicals",
  fundamentals: "Fundamentals",
  momentum: "Momentum",
  institutional: "Institutional",
  risk: "Risk",
  macro: "Macro",
};

function actionVariant(action: string): "bull" | "bear" | "warning" | "default" {
  if (action === "strong_buy" || action === "buy") return "bull";
  if (action === "avoid" || action === "reduce") return "bear";
  return "default";
}

function BreakdownBar({ label, value }: { label: string; value: number }) {
  const color = value >= 65 ? "bg-bull" : value <= 35 ? "bg-bear" : "bg-warning";
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px] text-muted">
        <span>{label}</span>
        <span className="font-medium text-foreground">{Math.round(value)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel-hover">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

export function RecommendationCard({
  recommendation,
  currency,
}: {
  recommendation: Recommendation | null;
  currency: string;
}) {
  const [expanded, setExpanded] = React.useState(false);

  if (!recommendation) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>AI Recommendation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted">No active recommendation for this company yet.</p>
        </CardContent>
      </Card>
    );
  }

  const r = recommendation;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>AI Recommendation</CardTitle>
        <Badge variant={actionVariant(r.action)}>{r.action.replace("_", " ").toUpperCase()}</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <ScoreGauge score={r.master_score} size={72} label="Score" />
          <div className="grid flex-1 grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <div>
              <p className="text-muted">Entry Zone</p>
              <p className="font-mono font-medium">
                {formatCurrency(r.entry_zone_low, currency)} – {formatCurrency(r.entry_zone_high, currency)}
              </p>
            </div>
            <div>
              <p className="text-muted">Stop Loss</p>
              <p className="font-mono font-medium text-bear">{formatCurrency(r.stop_loss, currency)}</p>
            </div>
            <div>
              <p className="text-muted">Targets</p>
              <p className="font-mono font-medium text-bull">
                {formatCurrency(r.take_profit_1, currency)} / {formatCurrency(r.take_profit_2, currency)} /{" "}
                {formatCurrency(r.take_profit_3, currency)}
              </p>
            </div>
            <div>
              <p className="text-muted">Risk/Reward</p>
              <p className="font-mono font-medium">{r.risk_reward}</p>
            </div>
            <div>
              <p className="text-muted">Confidence</p>
              <p className="font-medium">{Math.round(r.confidence * 100)}%</p>
            </div>
            <div>
              <p className="text-muted">Holding Period</p>
              <p className="font-medium capitalize">{r.holding_period}</p>
            </div>
          </div>
        </div>

        {r.score_breakdown && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border pt-3">
            {(Object.entries(r.score_breakdown) as [keyof ScoreBreakdown, number][]).map(([key, value]) => (
              <BreakdownBar key={key} label={BREAKDOWN_LABELS[key]} value={value} />
            ))}
          </div>
        )}

        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex w-full items-center justify-between border-t border-border pt-3 text-xs text-muted hover:text-foreground"
        >
          Why this recommendation?
          <ChevronDown className={`size-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} />
        </button>
        {expanded && (
          <div className="space-y-2 text-xs">
            <p className="text-foreground">{r.explanation}</p>
            {r.pros.length > 0 && (
              <div>
                <p className="mb-1 text-muted">Pros</p>
                <ul className="list-disc space-y-0.5 pl-4 text-bull">
                  {r.pros.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
            {r.cons.length > 0 && (
              <div>
                <p className="mb-1 text-muted">Cons</p>
                <ul className="list-disc space-y-0.5 pl-4 text-bear">
                  {r.cons.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="italic text-warning">{r.uncertainty_note}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
