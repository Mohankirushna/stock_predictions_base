import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import type { Company } from "@/types/models";

export function CompetitorsTab({ competitors }: { competitors: Company[] }) {
  if (competitors.length === 0) return <p className="text-sm text-muted">No competitors found for this sector.</p>;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {competitors.map((c) => (
        <Link
          key={c.id}
          href={`/companies/${c.symbol}`}
          className="rounded-md border border-border p-3 hover:bg-panel-hover"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium">{c.symbol}</span>
            <Badge variant="outline">{c.exchange}</Badge>
          </div>
          <p className="mt-1 truncate text-xs text-muted">{c.name}</p>
          <p className="mt-1 text-[11px] text-muted">{c.industry}</p>
        </Link>
      ))}
    </div>
  );
}
