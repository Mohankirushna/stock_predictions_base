import type * as React from "react";

import { Badge } from "@/components/ui/badge";
import { MacdPane } from "@/components/charts/indicator-panes";
import type { Technicals } from "@/types/models";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-1.5 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

const SIGNAL_LABELS: Record<string, string> = {
  golden_cross: "Golden Cross",
  death_cross: "Death Cross",
  breakout: "Breakout",
  breakdown: "Breakdown",
  volume_spike: "Volume Spike",
};

export function TechnicalsTab({ technicals }: { technicals: Technicals | null }) {
  if (!technicals) return <p className="text-sm text-muted">Technicals have not been computed for this company yet.</p>;

  const activeSignals = Object.entries(technicals.signals)
    .filter(([key, value]) => key !== "patterns" && value === true)
    .map(([key]) => SIGNAL_LABELS[key] ?? key);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-muted">Moving Averages</h4>
        <Row label="EMA 20" value={technicals.ema_20 ?? "—"} />
        <Row label="EMA 50" value={technicals.ema_50 ?? "—"} />
        <Row label="EMA 200" value={technicals.ema_200 ?? "—"} />
        <Row label="VWAP" value={technicals.vwap ?? "—"} />

        <h4 className="mb-2 mt-4 text-xs font-semibold uppercase text-muted">Bollinger Bands</h4>
        <Row label="Upper" value={technicals.bb_upper ?? "—"} />
        <Row label="Mid" value={technicals.bb_mid ?? "—"} />
        <Row label="Lower" value={technicals.bb_lower ?? "—"} />
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-muted">Momentum</h4>
        <Row label="RSI (14)" value={technicals.rsi_14 ?? "—"} />
        <Row label="ATR (14)" value={technicals.atr_14 ?? "—"} />
        <div className="py-2">
          <MacdPane technicals={technicals} />
        </div>

        <h4 className="mb-2 mt-4 text-xs font-semibold uppercase text-muted">Trend &amp; Signals</h4>
        <div className="flex flex-wrap gap-1.5">
          <Badge variant={technicals.trend.includes("up") ? "bull" : technicals.trend.includes("down") ? "bear" : "default"}>
            {technicals.trend.replace("_", " ")}
          </Badge>
          {activeSignals.map((s) => (
            <Badge key={s} variant="accent">
              {s}
            </Badge>
          ))}
          {technicals.signals.patterns.map((p) => (
            <Badge key={p} variant="warning">
              {p}
            </Badge>
          ))}
        </div>

        {(technicals.support.length > 0 || technicals.resistance.length > 0) && (
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="mb-1 text-muted">Support</p>
              {technicals.support.map((s) => (
                <p key={s.price} className="font-mono text-bull">
                  ${s.price}
                </p>
              ))}
            </div>
            <div>
              <p className="mb-1 text-muted">Resistance</p>
              {technicals.resistance.map((r) => (
                <p key={r.price} className="font-mono text-bear">
                  ${r.price}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
