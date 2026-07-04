import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChangeBadge } from "@/components/dashboard/change-badge";
import { formatCurrency } from "@/lib/utils";
import type { Mover } from "@/types/models";

export function MoversList({ title, movers }: { title: string; movers: Mover[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {movers.length === 0 && <p className="text-sm text-muted">No data yet.</p>}
        {movers.map((m) => (
          <Link
            key={m.symbol}
            href={`/companies/${m.symbol}`}
            className="flex items-center justify-between gap-2 rounded-md p-1.5 -mx-1.5 hover:bg-panel-hover"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{m.symbol}</p>
              <p className="truncate text-xs text-muted">{m.name}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-0.5">
              <span className="font-tabular text-sm">{formatCurrency(m.price, m.currency)}</span>
              <ChangeBadge value={m.change_pct} />
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
