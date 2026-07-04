"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreGauge } from "@/components/charts/score-gauge";
import type { Opportunity } from "@/types/models";

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const [expanded, setExpanded] = useState(false);
  const confidencePct = Math.round(opportunity.confidence * 100);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <ScoreGauge score={confidencePct} size={52} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Link href={`/companies/${opportunity.symbol}`} className="font-semibold hover:text-accent">
                {opportunity.symbol}
              </Link>
              <span className="truncate text-xs text-muted">{opportunity.company_name}</span>
            </div>
            <p className="mt-1 text-xs text-muted">
              Entry {opportunity.entry_zone_low}–{opportunity.entry_zone_high} · {confidencePct}% confidence
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {opportunity.catalysts.slice(0, 3).map((c) => (
                <Badge key={c} variant="accent">
                  {c}
                </Badge>
              ))}
            </div>
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
            <ul className="list-disc space-y-1 pl-4 text-muted">
              {opportunity.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            <p className="text-warning">Risk: {opportunity.risk}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
