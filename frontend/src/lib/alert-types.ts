import type { AlertType } from "@/types/models";

export const ALERT_TYPES: { value: AlertType; label: string }[] = [
  { value: "breakout", label: "Breakout" },
  { value: "support_break", label: "Support Break" },
  { value: "resistance_break", label: "Resistance Break" },
  { value: "volume_spike", label: "Volume Spike" },
  { value: "sentiment_shift", label: "Sentiment Shift" },
  { value: "analyst_upgrade", label: "Analyst Upgrade" },
  { value: "confidence_change", label: "Confidence Change" },
  { value: "price_target", label: "Price Target" },
];
