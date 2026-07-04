"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { OpportunityCard } from "@/components/dashboard/opportunity-card";
import { RecommendationRow } from "@/components/research/recommendation-row";
import { listOpportunities, screenRecommendations } from "@/lib/api/research";
import type { Opportunity, Recommendation } from "@/types/models";

export default function ResearchPage() {
  const [opportunities, setOpportunities] = React.useState<Opportunity[]>([]);
  const [recommendations, setRecommendations] = React.useState<Recommendation[]>([]);
  const [minScore, setMinScore] = React.useState(0);
  const [sector, setSector] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [total, setTotal] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    listOpportunities()
      .then(setOpportunities)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load opportunities"));
  }, []);

  React.useEffect(() => {
    screenRecommendations({ minScore, sector: sector || undefined, page })
      .then((res) => {
        setRecommendations(res.data);
        setTotal(res.meta.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load recommendations"));
  }, [minScore, sector, page]);

  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div>
      <PageHeader title="Research" description="AI-generated reports and the opportunity screener." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <div className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-muted">AI Opportunities</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {opportunities.length === 0 && <p className="text-sm text-muted">No opportunities discovered yet.</p>}
          {opportunities.map((o) => (
            <OpportunityCard key={o.symbol} opportunity={o} />
          ))}
        </div>
      </div>

      <div>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="text-sm font-semibold text-muted">Recommendation Screener</h2>
          <div className="ml-auto flex gap-2">
            <Input
              placeholder="Min score"
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => {
                setMinScore(Number(e.target.value) || 0);
                setPage(1);
              }}
              className="w-28"
            />
            <Input
              placeholder="Sector"
              value={sector}
              onChange={(e) => {
                setSector(e.target.value);
                setPage(1);
              }}
              className="w-40"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {recommendations.length === 0 && <p className="text-sm text-muted">No recommendations match these filters.</p>}
          {recommendations.map((r) => (
            <RecommendationRow key={r.id} recommendation={r} />
          ))}
        </div>

        {total > 0 && (
          <div className="mt-4 flex items-center justify-between text-sm text-muted">
            <span>
              Page {page} of {totalPages} &middot; {total} recommendations
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
