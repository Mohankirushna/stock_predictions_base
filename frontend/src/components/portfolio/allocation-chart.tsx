"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = [
  "var(--color-accent)",
  "var(--color-bull)",
  "var(--color-warning)",
  "var(--color-bear)",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
];

export function AllocationChart({ title, breakdown }: { title: string; breakdown: Record<string, number> }) {
  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  const data = entries.map(([name, value]) => ({ name, value }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-sm text-muted">No holdings yet.</p>
        ) : (
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" innerRadius={40} outerRadius={65} strokeWidth={2}>
                  {data.map((d, i) => (
                    <Cell key={d.name} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-1.5 text-xs">
              {data.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 truncate">
                    <span className="size-2 shrink-0 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    {d.name}
                  </span>
                  <span className="font-medium">{d.value.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
