"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreGauge } from "@/components/charts/score-gauge";
import type { Recommendation } from "@/types/models";

function actionVariant(action: string): "bull" | "bear" | "default" {
  if (action === "strong_buy" || action === "buy") return "bull";
  if (action === "avoid" || action === "reduce") return "bear";
  return "default";
}

export function RecommendationRow({ recommendation }: { recommendation: Recommendation }) {
  const [expanded, setExpanded] = React.useState(false);
  const r = recommendation;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <ScoreGauge score={r.master_score} size={48} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Link href={`/companies/${r.symbol}`} className="font-semibold hover:text-accent">
                {r.symbol}
              </Link>
              <Badge variant={actionVariant(r.action)}>{r.action.replace("_", " ")}</Badge>
              <span className="text-xs text-muted">{Math.round(r.confidence * 100)}% confidence</span>
            </div>
            <p className="mt-1 text-xs text-muted">
              Entry ${r.entry_zone_low}&ndash;${r.entry_zone_high} &middot; Stop ${r.stop_loss} &middot; R/R {r.risk_reward}
            </p>
          </div>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 flex w-full items-center justify-between text-xs text-muted hover:text-foreground"
        >
          Why?
          <ChevronDown className={`size-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} />
        </button>
        {expanded && (
          <div className="mt-2 space-y-2 border-t border-border pt-2 text-xs">
            <p>{r.explanation}</p>
            {r.pros.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-4 text-bull">
                {r.pros.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            )}
            {r.cons.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-4 text-bear">
                {r.cons.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            )}
            <p className="italic text-warning">{r.uncertainty_note}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
