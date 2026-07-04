"use client";

import * as React from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PriceBar, Technicals } from "@/types/models";

interface Candle {
  ts: string;
  label: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  bullish: boolean;
}

function toCandles(bars: PriceBar[]): Candle[] {
  return bars.map((b) => {
    const open = Number(b.open);
    const high = Number(b.high);
    const low = Number(b.low);
    const close = Number(b.close);
    return {
      ts: b.ts,
      label: new Date(b.ts).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      open, high, low, close,
      volume: Number(b.volume),
      bullish: close >= open,
    };
  });
}

interface CandleShapeProps {
  x?: number;
  width?: number;
  y?: number;
  height?: number;
  payload?: Candle;
}

// Recharts has no native candlestick geometry — render bodies as a Bar with a
// custom shape so each bar draws its own wick + body from the OHLC values.
function CandleShape(props: CandleShapeProps) {
  const { x = 0, width = 0, y = 0, height = 0, payload } = props;
  if (!payload) return null;
  const { open, high, low, close, bullish } = payload;
  const color = bullish ? "var(--color-bull)" : "var(--color-bear)";

  const range = high - low || 1;
  const px = (v: number) => y + height - ((v - low) / range) * height;

  const bodyTop = px(Math.max(open, close));
  const bodyBottom = px(Math.min(open, close));
  const cx = x + width / 2;

  return (
    <g>
      <line x1={cx} x2={cx} y1={px(high)} y2={px(low)} stroke={color} strokeWidth={1} />
      <rect
        x={x + width * 0.2}
        y={bodyTop}
        width={width * 0.6}
        height={Math.max(bodyBottom - bodyTop, 1)}
        fill={color}
      />
    </g>
  );
}

function CandleTooltip({ active, payload }: { active?: boolean; payload?: { payload: Candle }[] }) {
  if (!active || !payload?.length) return null;
  const c: Candle = payload[0].payload;
  return (
    <div className="rounded-md border border-border bg-panel p-2 text-xs shadow-lg">
      <p className="mb-1 font-medium">{c.label}</p>
      <p>O {c.open.toFixed(2)} &middot; H {c.high.toFixed(2)}</p>
      <p>L {c.low.toFixed(2)} &middot; C {c.close.toFixed(2)}</p>
      <p className="text-muted">Vol {c.volume.toLocaleString()}</p>
    </div>
  );
}

export function CandlestickChart({
  bars,
  technicals,
  entryLow,
  entryHigh,
  stopLoss,
  takeProfits,
}: {
  bars: PriceBar[];
  technicals?: Technicals | null;
  entryLow?: number;
  entryHigh?: number;
  stopLoss?: number;
  takeProfits?: number[];
}) {
  const data = React.useMemo(() => toCandles(bars), [bars]);
  const lows = data.map((d) => d.low);
  const highs = data.map((d) => d.high);
  const domainLow = lows.length ? Math.min(...lows, stopLoss ?? Infinity) * 0.98 : 0;
  const domainHigh = highs.length ? Math.max(...highs, ...(takeProfits ?? [])) * 1.02 : 100;

  if (data.length === 0) {
    return <div className="flex h-80 items-center justify-center text-sm text-muted">No price history yet.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--color-muted)" }} minTickGap={30} />
        <YAxis
          domain={[domainLow, domainHigh]}
          tick={{ fontSize: 11, fill: "var(--color-muted)" }}
          width={56}
          tickFormatter={(v) => Number(v).toFixed(0)}
        />
        <Tooltip content={<CandleTooltip />} />

        {entryLow !== undefined && entryHigh !== undefined && (
          <>
            <ReferenceLine y={entryHigh} stroke="var(--color-accent)" strokeDasharray="4 4" label={{ value: "Entry high", fontSize: 10, fill: "var(--color-accent)", position: "insideTopLeft" }} />
            <ReferenceLine y={entryLow} stroke="var(--color-accent)" strokeDasharray="4 4" label={{ value: "Entry low", fontSize: 10, fill: "var(--color-accent)", position: "insideBottomLeft" }} />
          </>
        )}
        {stopLoss !== undefined && (
          <ReferenceLine y={stopLoss} stroke="var(--color-bear)" strokeWidth={1.5} label={{ value: "Stop loss", fontSize: 10, fill: "var(--color-bear)", position: "insideBottomLeft" }} />
        )}
        {takeProfits?.map((tp, i) => (
          <ReferenceLine key={tp} y={tp} stroke="var(--color-bull)" strokeDasharray="2 2" label={{ value: `TP${i + 1}`, fontSize: 10, fill: "var(--color-bull)", position: "insideTopLeft" }} />
        ))}

        <Bar dataKey="high" shape={CandleShape} isAnimationActive={false} />
        {technicals?.ema_20 && (
          <Line type="monotone" dataKey={() => Number(technicals.ema_20)} stroke="var(--color-warning)" dot={false} strokeWidth={1} isAnimationActive={false} name="EMA20" />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
