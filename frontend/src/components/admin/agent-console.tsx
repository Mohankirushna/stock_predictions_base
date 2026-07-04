"use client";

import * as React from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const AGENTS = [
  { name: "data_collection", label: "Data Collection" },
  { name: "technical_analysis", label: "Technical Analysis" },
  { name: "fundamental_analysis", label: "Fundamental Analysis" },
  { name: "news_intelligence", label: "News Intelligence" },
  { name: "market_intelligence", label: "Market Intelligence" },
  { name: "research", label: "Research" },
  { name: "opportunity_discovery", label: "Opportunity Discovery" },
  { name: "recommendation", label: "Recommendation" },
  { name: "alert", label: "Alert" },
  { name: "learning", label: "Learning" },
];

export function AgentConsole({ onRun }: { onRun: (name: string) => Promise<{ task_id: string }> }) {
  const [running, setRunning] = React.useState<string | null>(null);
  const [lastResult, setLastResult] = React.useState<string | null>(null);

  async function handleRun(name: string) {
    setRunning(name);
    setLastResult(null);
    try {
      const { task_id } = await onRun(name);
      setLastResult(`Enqueued ${name} — task ${task_id.slice(0, 8)}…`);
    } catch (err) {
      setLastResult(err instanceof Error ? err.message : `Failed to run ${name}`);
    } finally {
      setRunning(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Console</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {AGENTS.map((a) => (
            <Button
              key={a.name}
              variant="outline"
              size="sm"
              disabled={running !== null}
              onClick={() => void handleRun(a.name)}
            >
              {running === a.name ? "Running…" : a.label}
            </Button>
          ))}
        </div>
        {lastResult && <p className="text-xs text-muted">{lastResult}</p>}
      </CardContent>
    </Card>
  );
}
