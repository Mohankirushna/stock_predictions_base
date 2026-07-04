"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search } from "lucide-react";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { listCompanies, searchExternal, trackCompany } from "@/lib/api/companies";
import type { SymbolMatch } from "@/types/models";

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<SymbolMatch[]>([]);
  const [trackingSymbol, setTrackingSymbol] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const router = useRouter();

  React.useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  React.useEffect(() => {
    if (!query.trim()) return;
    const handle = setTimeout(() => {
      Promise.all([
        listCompanies({ search: query, size: 8 }).then(({ data }) => data).catch(() => []),
        searchExternal(query).catch(() => []),
      ]).then(([tracked, external]) => {
        // Tracked (DB) results are authoritative — prefer them over an
        // external hit for the same symbol so a company we already have
        // real data for is never shown as "not tracked yet".
        const merged: SymbolMatch[] = tracked.map((c) => ({
          symbol: c.symbol, name: c.name, exchange: c.exchange, tracked: true,
        }));
        const seen = new Set(merged.map((m) => m.symbol));
        for (const m of external) {
          if (!seen.has(m.symbol)) {
            merged.push(m);
            seen.add(m.symbol);
          }
        }
        setResults(merged);
      });
    }, 250);
    return () => clearTimeout(handle);
  }, [query]);

  const visibleResults = query.trim() ? results : [];

  function goTo(symbol: string) {
    setOpen(false);
    setQuery("");
    router.push(`/companies/${symbol}`);
  }

  async function selectResult(match: SymbolMatch) {
    if (match.tracked) {
      goTo(match.symbol);
      return;
    }
    setError(null);
    setTrackingSymbol(match.symbol);
    try {
      await trackCompany(match.symbol);
      goTo(match.symbol);
    } catch {
      setError(`Couldn't fetch real data for ${match.symbol} — try again in a moment.`);
    } finally {
      setTrackingSymbol(null);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex h-8 w-64 shrink-0 items-center gap-2 whitespace-nowrap rounded-md border border-border bg-background px-3 text-sm text-muted transition-colors hover:border-accent/40"
      >
        <Search className="size-3.5" />
        Search companies…
        <kbd className="ml-auto rounded border border-border px-1.5 py-0.5 text-[10px]">⌘K</kbd>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg p-0" aria-describedby={undefined}>
          <DialogTitle className="sr-only">Search companies</DialogTitle>
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            <Search className="size-4 text-muted" />
            <Input
              autoFocus
              placeholder="Search any NSE/BSE stock by symbol or name…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="border-none bg-transparent px-0 shadow-none focus-visible:ring-0"
            />
          </div>
          <div className="max-h-80 overflow-y-auto p-2">
            {visibleResults.length === 0 && query.trim() && (
              <p className="px-2 py-4 text-center text-sm text-muted">No companies found.</p>
            )}
            {error && <p className="px-3 py-2 text-xs text-bear">{error}</p>}
            {visibleResults.map((m) => (
              <button
                key={m.symbol}
                onClick={() => selectResult(m)}
                disabled={trackingSymbol !== null}
                className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-panel-hover disabled:opacity-60"
              >
                <span className="flex items-center gap-2">
                  <span className="font-medium">{m.symbol}</span>
                  {!m.tracked && (
                    <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted">
                      {trackingSymbol === m.symbol ? "Fetching…" : "Fetch real data"}
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-2 truncate text-muted">
                  {trackingSymbol === m.symbol && <Loader2 className="size-3.5 animate-spin" />}
                  {m.name}
                </span>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
