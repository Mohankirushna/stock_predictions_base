import { Badge } from "@/components/ui/badge";
import type { Prediction } from "@/types/models";

function directionVariant(direction: string): "bull" | "bear" | "default" {
  if (direction === "up") return "bull";
  if (direction === "down") return "bear";
  return "default";
}

export function PredictionsTab({ predictions }: { predictions: Prediction[] }) {
  if (predictions.length === 0) return <p className="text-sm text-muted">No prediction history for this company yet.</p>;
  return (
    <div className="space-y-2">
      {predictions.map((p) => (
        <div key={p.id} className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-md border border-border p-3 text-sm">
          <div className="flex items-center gap-3">
            <Badge variant={directionVariant(p.expected_direction)}>{p.expected_direction.toUpperCase()}</Badge>
            <span className="text-muted">{p.horizon}</span>
          </div>
          <div className="font-mono text-xs">
            ${p.expected_range_low} – ${p.expected_range_high}
          </div>
          <div className="text-xs text-muted">{Math.round(p.confidence * 100)}% confidence</div>
          <div className="font-mono text-xs text-muted">from ${p.price_at_prediction}</div>
          <div className="ml-auto text-xs text-muted">{new Date(p.predicted_at).toLocaleDateString()}</div>
        </div>
      ))}
    </div>
  );
}
