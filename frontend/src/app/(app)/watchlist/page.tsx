"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { WatchlistRow, type WatchlistRowData } from "@/components/watchlist/watchlist-row";
import {
  addWatchlistItem,
  createWatchlist,
  deleteWatchlist,
  listWatchlists,
  removeWatchlistItem,
} from "@/lib/api/watchlists";
import { getCompany, getCompanyRecommendation, getPrices } from "@/lib/api/companies";
import type { Watchlist } from "@/types/models";

export default function WatchlistPage() {
  const [watchlists, setWatchlists] = React.useState<Watchlist[]>([]);
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [rows, setRows] = React.useState<WatchlistRowData[] | null>(null);
  const [newSymbol, setNewSymbol] = React.useState("");
  const [newListName, setNewListName] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    listWatchlists()
      .then((wl) => {
        setWatchlists(wl);
        setActiveId((prev) => prev ?? wl.find((w) => w.is_default)?.id ?? wl[0]?.id ?? null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load watchlists"));
  }, []);

  const active = watchlists.find((w) => w.id === activeId) ?? null;

  React.useEffect(() => {
    Promise.all(
      (active?.symbols ?? []).map(async (symbol) => {
        const [company, prices, recommendation] = await Promise.all([
          getCompany(symbol).catch(() => null),
          getPrices(symbol).catch(() => []),
          getCompanyRecommendation(symbol).catch(() => null),
        ]);
        return {
          symbol,
          company,
          latestBar: prices.at(-1) ?? null,
          prevBar: prices.at(-2) ?? null,
          recommendation,
        };
      })
    ).then(setRows);
  }, [active]);

  async function handleCreateList() {
    if (!newListName.trim()) return;
    const wl = await createWatchlist(newListName.trim(), watchlists.length === 0);
    setWatchlists((prev) => [...prev, wl]);
    setActiveId(wl.id);
    setNewListName("");
  }

  async function handleDeleteList() {
    if (!active) return;
    await deleteWatchlist(active.id);
    setWatchlists((prev) => prev.filter((w) => w.id !== active.id));
    setActiveId(null);
  }

  async function handleAddSymbol() {
    if (!active || !newSymbol.trim()) return;
    const symbol = newSymbol.trim().toUpperCase();
    try {
      const updated = await addWatchlistItem(active.id, symbol);
      setWatchlists((prev) => prev.map((w) => (w.id === active.id ? updated : w)));
      setNewSymbol("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add symbol");
    }
  }

  async function handleRemoveSymbol(symbol: string) {
    if (!active) return;
    await removeWatchlistItem(active.id, symbol);
    setWatchlists((prev) =>
      prev.map((w) => (w.id === active.id ? { ...w, symbols: w.symbols.filter((s) => s !== symbol) } : w))
    );
  }

  return (
    <div>
      <PageHeader title="Watchlist" description="Live prices and signals for the companies you're tracking." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {watchlists.map((w) => (
          <button
            key={w.id}
            onClick={() => setActiveId(w.id)}
            className={`rounded-md border px-3 py-1.5 text-sm ${
              w.id === activeId ? "border-accent bg-accent/10 text-accent" : "border-border text-muted hover:bg-panel-hover"
            }`}
          >
            {w.name}
            {w.is_default && <Badge variant="outline" className="ml-2">default</Badge>}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <Input
            placeholder="New watchlist name…"
            value={newListName}
            onChange={(e) => setNewListName(e.target.value)}
            className="h-9 w-48"
          />
          <Button size="sm" onClick={() => void handleCreateList()}>
            Create
          </Button>
        </div>
      </div>

      {watchlists.length === 0 ? (
        <Card className="p-4 text-sm text-muted">You don&rsquo;t have any watchlists yet. Create one above.</Card>
      ) : active ? (
        <>
          <div className="mb-4 flex items-center gap-2">
            <Input
              placeholder="Add symbol (e.g. AAPL)…"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleAddSymbol();
              }}
              className="max-w-xs"
            />
            <Button size="sm" onClick={() => void handleAddSymbol()}>
              Add
            </Button>
            <Button size="sm" variant="outline" className="ml-auto" onClick={() => void handleDeleteList()}>
              Delete Watchlist
            </Button>
          </div>

          <Card className="divide-y divide-border">
            {rows === null && <p className="p-4 text-sm text-muted">Loading…</p>}
            {rows !== null && rows.length === 0 && (
              <p className="p-4 text-sm text-muted">No symbols in this watchlist yet.</p>
            )}
            {rows?.map((row) => (
              <WatchlistRow key={row.symbol} row={row} onRemove={() => void handleRemoveSymbol(row.symbol)} />
            ))}
          </Card>
        </>
      ) : null}
    </div>
  );
}
