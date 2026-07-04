import { ArrowDown, ArrowUp } from "lucide-react";

import { cn, formatPct } from "@/lib/utils";

export function ChangeBadge({ value, className }: { value: number | string; className?: string }) {
  const num = typeof value === "string" ? Number(value) : value;
  const positive = num >= 0;
  const Icon = positive ? ArrowUp : ArrowDown;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 font-tabular text-xs font-medium",
        positive ? "text-bull" : "text-bear",
        className
      )}
    >
      <Icon className="size-3" />
      {formatPct(num)}
    </span>
  );
}
