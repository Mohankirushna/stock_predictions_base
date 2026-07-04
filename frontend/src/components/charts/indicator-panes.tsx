"use client";

import { Area, AreaChart, Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, YAxis } from "recharts";

import type { PriceBar, Technicals } from "@/types/models";

export function VolumePane({ bars }: { bars: PriceBar[] }) {
  const data = bars.map((b) => ({ ts: b.ts, volume: Number(b.volume), up: Number(b.close) >= Number(b.open) }));
  return (
    <ResponsiveContainer width="100%" height={60}>
      <BarChart data={data} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
        <YAxis hide domain={[0, "dataMax"]} />
        <Bar dataKey="volume" isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.ts} fill={d.up ? "var(--color-bull)" : "var(--color-bear)"} opacity={0.5} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RsiPane({ value }: { value: number | null }) {
  const v = value ?? 50;
  const data = [{ x: 0, rsi: v }, { x: 1, rsi: v }];
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px] text-muted">
        <span>RSI (14)</span>
        <span className={v >= 70 ? "text-bear" : v <= 30 ? "text-bull" : "text-foreground"}>{v.toFixed(1)}</span>
      </div>
      <ResponsiveContainer width="100%" height={40}>
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <YAxis hide domain={[0, 100]} />
          <ReferenceLine y={70} stroke="var(--color-bear)" strokeDasharray="2 2" />
          <ReferenceLine y={30} stroke="var(--color-bull)" strokeDasharray="2 2" />
          <Area type="monotone" dataKey="rsi" stroke="var(--color-accent)" fill="var(--color-accent)" fillOpacity={0.15} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MacdPane({ technicals }: { technicals: Technicals | null }) {
  if (!technicals?.macd) return null;
  const macd = Number(technicals.macd);
  const signal = Number(technicals.macd_signal ?? 0);
  const hist = Number(technicals.macd_hist ?? macd - signal);
  return (
    <div className="grid grid-cols-3 gap-2 text-[11px]">
      <div>
        <p className="text-muted">MACD</p>
        <p className="font-medium">{macd.toFixed(2)}</p>
      </div>
      <div>
        <p className="text-muted">Signal</p>
        <p className="font-medium">{signal.toFixed(2)}</p>
      </div>
      <div>
        <p className="text-muted">Histogram</p>
        <p className={hist >= 0 ? "font-medium text-bull" : "font-medium text-bear"}>{hist.toFixed(2)}</p>
      </div>
    </div>
  );
}
