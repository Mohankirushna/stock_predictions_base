"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

export function RecordTransactionDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (input: { symbol: string; side: "buy" | "sell"; quantity: string; price: string; fees?: string; note?: string }) => Promise<void>;
}) {
  const [symbol, setSymbol] = React.useState("");
  const [side, setSide] = React.useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = React.useState("");
  const [price, setPrice] = React.useState("");
  const [fees, setFees] = React.useState("");
  const [note, setNote] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim() || !quantity || !price) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        symbol: symbol.trim().toUpperCase(),
        side,
        quantity,
        price,
        fees: fees || undefined,
        note: note || undefined,
      });
      setSymbol("");
      setQuantity("");
      setPrice("");
      setFees("");
      setNote("");
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record transaction");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Transaction</DialogTitle>
          <DialogDescription>Log a buy or sell to update your holdings and P&amp;L.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex gap-2">
            <Button
              type="button"
              variant={side === "buy" ? "default" : "outline"}
              size="sm"
              className="flex-1"
              onClick={() => setSide("buy")}
            >
              Buy
            </Button>
            <Button
              type="button"
              variant={side === "sell" ? "default" : "outline"}
              size="sm"
              className="flex-1"
              onClick={() => setSide("sell")}
            >
              Sell
            </Button>
          </div>
          <Input placeholder="Symbol (e.g. AAPL)" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
          <div className="grid grid-cols-2 gap-2">
            <Input
              placeholder="Quantity"
              type="number"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
            <Input
              placeholder="Price"
              type="number"
              step="any"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              required
            />
          </div>
          <Input placeholder="Fees (optional)" type="number" step="any" value={fees} onChange={(e) => setFees(e.target.value)} />
          <Input placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          {error && <p className="text-sm text-bear">{error}</p>}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Recording…" : "Record Transaction"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
