"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ALERT_TYPES } from "@/lib/alert-types";
import type { AlertType } from "@/types/models";

export function CreateAlertDialog({
  symbol,
  open,
  onOpenChange,
  onCreate,
}: {
  symbol: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (alertType: AlertType) => Promise<void>;
}) {
  const [creating, setCreating] = React.useState(false);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Alert for {symbol}</DialogTitle>
          <DialogDescription>Choose what should trigger a notification.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-2">
          {ALERT_TYPES.map((t) => (
            <Button
              key={t.value}
              variant="outline"
              size="sm"
              disabled={creating}
              onClick={async () => {
                setCreating(true);
                try {
                  await onCreate(t.value);
                  onOpenChange(false);
                } finally {
                  setCreating(false);
                }
              }}
            >
              {t.label}
            </Button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
