"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ALERT_TYPES } from "@/lib/alert-types";
import type { AlertType } from "@/types/models";

export function CreateAlertDialog({
  open,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (symbol: string, alertType: AlertType) => Promise<void>;
}) {
  const [symbol, setSymbol] = React.useState("");
  const [alertType, setAlertType] = React.useState<AlertType>("breakout");
  const [creating, setCreating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await onCreate(symbol.trim().toUpperCase(), alertType);
      setSymbol("");
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create alert");
    } finally {
      setCreating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Alert</DialogTitle>
          <DialogDescription>Choose a symbol and what should trigger a notification.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Input placeholder="Symbol (e.g. AAPL)" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
          <div className="grid grid-cols-2 gap-2">
            {ALERT_TYPES.map((t) => (
              <Button
                key={t.value}
                type="button"
                variant={alertType === t.value ? "default" : "outline"}
                size="sm"
                onClick={() => setAlertType(t.value)}
              >
                {t.label}
              </Button>
            ))}
          </div>
          {error && <p className="text-sm text-bear">{error}</p>}
          <Button type="submit" disabled={creating} className="w-full">
            {creating ? "Creating…" : "Create Alert"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
