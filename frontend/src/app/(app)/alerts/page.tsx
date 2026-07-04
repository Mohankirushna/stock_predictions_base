"use client";

import * as React from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertRow } from "@/components/alerts/alert-row";
import { CreateAlertDialog } from "@/components/alerts/create-alert-dialog";
import { NotificationItem } from "@/components/alerts/notification-item";
import { createAlert, deleteAlert, listAlerts, listNotifications, markAllNotificationsRead, updateAlert } from "@/lib/api/alerts";
import { useNotificationsStore } from "@/stores/notifications-store";
import type { Alert, AlertType } from "@/types/models";

export default function AlertsPage() {
  const [alerts, setAlerts] = React.useState<Alert[] | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const notifications = useNotificationsStore((s) => s.items);
  const setAllNotifications = useNotificationsStore((s) => s.setAll);
  const markAllReadLocal = useNotificationsStore((s) => s.markAllRead);
  const unreadCount = useNotificationsStore((s) => s.unreadCount);

  React.useEffect(() => {
    listAlerts()
      .then(setAlerts)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load alerts"));
    listNotifications()
      .then((res) => setAllNotifications(res.data))
      .catch(() => {});
  }, [setAllNotifications]);

  async function handleCreate(symbol: string, alertType: AlertType) {
    const alert = await createAlert({ symbol, alert_type: alertType });
    setAlerts((prev) => [alert, ...(prev ?? [])]);
  }

  async function handleToggleActive(alert: Alert) {
    const updated = await updateAlert(alert.id, { is_active: !alert.is_active });
    setAlerts((prev) => (prev ?? []).map((a) => (a.id === alert.id ? updated : a)));
  }

  async function handleDelete(alert: Alert) {
    await deleteAlert(alert.id);
    setAlerts((prev) => (prev ?? []).filter((a) => a.id !== alert.id));
  }

  async function handleMarkAllRead() {
    await markAllNotificationsRead();
    markAllReadLocal();
  }

  return (
    <div>
      <PageHeader title="Alerts" description="Rule builder, trigger history, and live notifications." />

      {error && <p className="mb-4 text-sm text-bear">{error}</p>}

      <Tabs defaultValue="alerts">
        <TabsList>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="notifications">
            Notifications{unreadCount > 0 ? ` (${unreadCount})` : ""}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="alerts">
          <div className="mb-4 flex justify-end">
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              + New Alert
            </Button>
          </div>
          <div className="space-y-2">
            {alerts === null && <p className="text-sm text-muted">Loading…</p>}
            {alerts?.length === 0 && <Card className="p-4 text-sm text-muted">No alerts configured yet.</Card>}
            {alerts?.map((a) => (
              <AlertRow
                key={a.id}
                alert={a}
                onToggleActive={() => void handleToggleActive(a)}
                onDelete={() => void handleDelete(a)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="notifications">
          <div className="mb-4 flex justify-end">
            <Button size="sm" variant="outline" onClick={() => void handleMarkAllRead()} disabled={unreadCount === 0}>
              Mark all read
            </Button>
          </div>
          <Card className="divide-y divide-border">
            {notifications.length === 0 && <p className="p-4 text-sm text-muted">No notifications yet.</p>}
            {notifications.map((n) => (
              <NotificationItem key={n.id} notification={n} />
            ))}
          </Card>
        </TabsContent>
      </Tabs>

      <CreateAlertDialog open={dialogOpen} onOpenChange={setDialogOpen} onCreate={handleCreate} />
    </div>
  );
}
