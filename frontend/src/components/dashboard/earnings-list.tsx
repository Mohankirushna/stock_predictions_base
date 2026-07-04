import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MarketEvent } from "@/types/models";

export function EarningsList({ events }: { events: MarketEvent[] }) {
  const earnings = events.filter((e) => e.event_type === "earnings");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upcoming Earnings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {earnings.length === 0 && <p className="text-sm text-muted">No upcoming earnings in this window.</p>}
        {earnings.map((e, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <span className="truncate">{e.company_symbol ?? e.title}</span>
            <span className="text-xs text-muted">
              {new Date(e.scheduled_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
