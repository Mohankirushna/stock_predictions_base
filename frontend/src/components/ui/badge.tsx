import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "border-border bg-panel-hover text-foreground",
        bull: "border-bull/30 bg-bull/10 text-bull",
        bear: "border-bear/30 bg-bear/10 text-bear",
        accent: "border-accent/30 bg-accent/10 text-accent",
        warning: "border-warning/30 bg-warning/10 text-warning",
        outline: "border-border text-muted bg-transparent",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}

export { Badge, badgeVariants };
