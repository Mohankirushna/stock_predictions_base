"use client";

import * as React from "react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listCompanies } from "@/lib/api/companies";
import type { Company } from "@/types/models";

const PAGE_SIZE = 20;

export default function CompaniesPage() {
  const [search, setSearch] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [companies, setCompanies] = React.useState<Company[]>([]);
  const [total, setTotal] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    listCompanies({ search: search || undefined, page, size: PAGE_SIZE })
      .then((res) => {
        setCompanies(res.data);
        setTotal(res.meta.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load companies"));
  }, [search, page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader title="Companies" description="Browse and search the full company directory." />

      <Input
        placeholder="Search by symbol or name…"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className="mb-4 max-w-sm"
      />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <Card className="divide-y divide-border">
        {companies.length === 0 && <p className="p-4 text-sm text-muted">No companies found.</p>}
        {companies.map((c) => (
          <Link
            key={c.id}
            href={`/companies/${c.symbol}`}
            className="flex items-center justify-between p-3 hover:bg-panel-hover"
          >
            <div className="flex items-center gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-panel-hover text-xs font-semibold text-accent">
                {c.symbol.slice(0, 2)}
              </div>
              <div>
                <p className="font-medium">{c.symbol}</p>
                <p className="text-xs text-muted">{c.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{c.exchange}</Badge>
              <Badge variant="default">{c.sector}</Badge>
            </div>
          </Link>
        ))}
      </Card>

      {total > 0 && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted">
          <span>
            Page {page} of {totalPages} &middot; {total} companies
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
  );
}
