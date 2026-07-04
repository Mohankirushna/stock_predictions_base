import { Card } from "@/components/ui/card";
import type { AdminStats } from "@/types/models";

export function StatsCards({ stats }: { stats: AdminStats }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Card className="p-3">
        <p className="text-[11px] text-muted">Total Users</p>
        <p className="font-tabular text-lg font-semibold">{stats.total_users}</p>
      </Card>
      <Card className="p-3">
        <p className="text-[11px] text-muted">Active Alerts</p>
        <p className="font-tabular text-lg font-semibold">{stats.active_alerts}</p>
      </Card>
      <Card className="p-3">
        <p className="text-[11px] text-muted">Recommendations</p>
        <p className="font-tabular text-lg font-semibold">{stats.total_recommendations}</p>
      </Card>
      <Card className="p-3">
        <p className="text-[11px] text-muted">AI Spend</p>
        <p className="font-tabular text-lg font-semibold">${stats.ai_spend_usd.toFixed(2)}</p>
      </Card>
    </div>
  );
}
