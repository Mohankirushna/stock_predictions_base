import { Card } from "@/components/ui/card";
import type { AIUsageEntry } from "@/types/models";

export function AiUsageTable({ entries }: { entries: AIUsageEntry[] }) {
  if (entries.length === 0) {
    return <Card className="p-4 text-sm text-muted">No AI usage recorded yet.</Card>;
  }
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted">
            <th className="p-3 font-medium">Provider</th>
            <th className="p-3 font-medium">Model</th>
            <th className="p-3 font-medium">Agent</th>
            <th className="p-3 text-right font-medium">Tokens In</th>
            <th className="p-3 text-right font-medium">Tokens Out</th>
            <th className="p-3 text-right font-medium">Cost</th>
            <th className="p-3 font-medium">When</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((e, i) => (
            <tr key={i} className="hover:bg-panel-hover">
              <td className="p-3">{e.provider}</td>
              <td className="p-3 text-muted">{e.model}</td>
              <td className="p-3 text-muted">{e.agent}</td>
              <td className="p-3 text-right font-tabular">{e.tokens_in.toLocaleString()}</td>
              <td className="p-3 text-right font-tabular">{e.tokens_out.toLocaleString()}</td>
              <td className="p-3 text-right font-tabular">${e.cost_usd.toFixed(4)}</td>
              <td className="p-3 text-xs text-muted">{e.created_at ? new Date(e.created_at).toLocaleString() : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
