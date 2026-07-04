"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { StatsCards } from "@/components/admin/stats-cards";
import { ScoreWeightsEditor } from "@/components/admin/score-weights-editor";
import { AgentConsole } from "@/components/admin/agent-console";
import { AiUsageTable } from "@/components/admin/ai-usage-table";
import { getAdminSettings, getAdminStats, getAiUsage, runAgent, updateAdminSettings } from "@/lib/api/admin";
import type { AdminSettings, AdminStats, AIUsageEntry } from "@/types/models";

export default function AdminPage() {
  const [stats, setStats] = React.useState<AdminStats | null>(null);
  const [settings, setSettings] = React.useState<AdminSettings | null>(null);
  const [usage, setUsage] = React.useState<AIUsageEntry[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    Promise.all([getAdminStats(), getAdminSettings(), getAiUsage()])
      .then(([s, cfg, u]) => {
        setStats(s);
        setSettings(cfg);
        setUsage(u);
      })
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load admin data — this page requires an admin account."
        )
      );
  }, []);

  async function handleSaveWeights(weights: Record<string, number>) {
    const updated = await updateAdminSettings(weights);
    setSettings(updated);
  }

  return (
    <div>
      <PageHeader title="Admin" description="AI provider config, score weights, spend, and agent console." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      {stats && (
        <div className="mb-6">
          <StatsCards stats={stats} />
        </div>
      )}

      {settings && (
        <div className="mb-6">
          <ScoreWeightsEditor settings={settings} onSave={handleSaveWeights} />
        </div>
      )}

      <div className="mb-6">
        <AgentConsole onRun={runAgent} />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-muted">Recent AI Usage</h2>
        <AiUsageTable entries={usage} />
      </div>
    </div>
  );
}
