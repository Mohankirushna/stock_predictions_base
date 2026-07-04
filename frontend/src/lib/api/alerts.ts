import { apiDelete, apiGet, apiGetPaginated, apiPatch, apiPost } from "@/lib/api/client";
import type { Alert, AlertType, Notification } from "@/types/models";

export async function listAlerts(): Promise<Alert[]> {
  return apiGet<Alert[]>("/api/v1/alerts");
}

export async function createAlert(input: {
  symbol: string;
  alert_type: AlertType;
  condition?: Record<string, unknown>;
  cooldown_minutes?: number;
}): Promise<Alert> {
  return apiPost<Alert>("/api/v1/alerts", input);
}

export async function updateAlert(
  id: string,
  input: { is_active?: boolean; condition?: Record<string, unknown>; cooldown_minutes?: number }
): Promise<Alert> {
  return apiPatch<Alert>(`/api/v1/alerts/${id}`, input);
}

export async function deleteAlert(id: string): Promise<void> {
  await apiDelete<void>(`/api/v1/alerts/${id}`);
}

export async function listNotifications(unread = false, page = 1) {
  return apiGetPaginated<Notification[]>(`/api/v1/notifications?unread=${unread}&page=${page}`);
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  return apiPost<{ marked_read: number }>("/api/v1/notifications/read-all");
}
