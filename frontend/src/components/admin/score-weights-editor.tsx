"use client";

import * as React from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AdminSettings } from "@/types/models";

export function ScoreWeightsEditor({
  settings,
  onSave,
}: {
  settings: AdminSettings;
  onSave: (weights: Record<string, number>) => Promise<void>;
}) {
  const [weights, setWeights] = React.useState(() => settings.score_weights);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const total = Object.values(weights).reduce((sum, v) => sum + v, 0);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await onSave(weights);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save weights");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Master Score Weights</CardTitle>
        <Badge variant={Math.abs(total - 1) < 0.01 || Math.abs(total - 100) < 0.5 ? "bull" : "warning"}>
          Total {total.toFixed(2)}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Object.entries(weights).map(([key, value]) => (
            <div key={key}>
              <label className="mb-1 block text-xs capitalize text-muted">{key}</label>
              <Input
                type="number"
                step="0.01"
                value={value}
                onChange={(e) => setWeights((prev) => ({ ...prev, [key]: Number(e.target.value) || 0 }))}
              />
            </div>
          ))}
        </div>
        <div className="border-t border-border pt-2 text-xs text-muted">
          Provider: <span className="font-medium text-foreground">{settings.ai_provider}</span>
          {settings.ai_fallback_providers.length > 0 && (
            <> &middot; Fallbacks: {settings.ai_fallback_providers.join(", ")}</>
          )}
        </div>
        {error && <p className="text-sm text-bear">{error}</p>}
        <Button size="sm" onClick={() => void handleSave()} disabled={saving}>
          {saving ? "Saving…" : "Save Weights"}
        </Button>
      </CardContent>
    </Card>
  );
}
