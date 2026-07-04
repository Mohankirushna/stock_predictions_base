import Link from "next/link";
import { Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ALERT_TYPES } from "@/lib/alert-types";
import type { Alert } from "@/types/models";

function typeLabel(type: string): string {
  return ALERT_TYPES.find((t) => t.value === type)?.label ?? type;
}

export function AlertRow({
  alert,
  onToggleActive,
  onDelete,
}: {
  alert: Alert;
  onToggleActive: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border p-3 text-sm">
      <div className="flex items-center gap-3">
        <Link href={`/companies/${alert.symbol}`} className="font-medium hover:text-accent">
          {alert.symbol}
        </Link>
        <Badge variant="accent">{typeLabel(alert.alert_type)}</Badge>
        <span className="text-xs text-muted">
          Cooldown {alert.cooldown_minutes}m
          {alert.last_triggered_at && ` · last triggered ${new Date(alert.last_triggered_at).toLocaleDateString()}`}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button variant={alert.is_active ? "subtle" : "outline"} size="sm" onClick={onToggleActive}>
          {alert.is_active ? "Active" : "Paused"}
        </Button>
        <Button variant="ghost" size="icon" onClick={onDelete} aria-label={`Delete alert for ${alert.symbol}`}>
          <Trash2 className="size-4" />
        </Button>
      </div>
    </div>
  );
}
