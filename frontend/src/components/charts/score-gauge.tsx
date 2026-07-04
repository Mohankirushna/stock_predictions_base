"use client";

import { cn } from "@/lib/utils";

function colorFor(score: number): string {
  if (score >= 65) return "var(--bull)";
  if (score <= 35) return "var(--bear)";
  return "var(--warning)";
}

/** Radial 0-100 score gauge (master score, health grade composite, etc.)
 * via a plain SVG arc — no charting-library overhead for a single value. */
export function ScoreGauge({
  score,
  size = 64,
  label,
  className,
}: {
  score: number;
  size?: number;
  label?: string;
  className?: string;
}) {
  const stroke = size * 0.11;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const color = colorFor(clamped);

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="var(--border)" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="font-tabular text-sm font-semibold leading-none" style={{ color }}>
          {Math.round(clamped)}
        </span>
        {label && <span className="mt-0.5 text-[9px] text-muted">{label}</span>}
      </div>
    </div>
  );
}
