import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { MarketEvent } from "@/types/models";

export function MarketEventsList({ events }: { events: MarketEvent[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Macro Calendar</CardTitle>
      </CardHeader>
      <CardContent className="max-h-[28rem] space-y-2 overflow-y-auto">
        {events.length === 0 && <p className="text-sm text-muted">No scheduled events in this window.</p>}
        {events.map((e, i) => (
          <div key={i} className="flex items-center justify-between rounded-md p-1.5 -mx-1.5 text-sm hover:bg-panel-hover">
            <div className="min-w-0">
              <p className="truncate">{e.title}</p>
              <p className="text-[11px] text-muted">
                {e.company_symbol ?? "Macro"} &middot; {e.event_type.replace("_", " ")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {e.importance >= 7 && <Badge variant="warning">High</Badge>}
              <span className="whitespace-nowrap text-xs text-muted">
                {new Date(e.scheduled_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
