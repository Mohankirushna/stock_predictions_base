"use client";

import { useAuth } from "@/hooks/use-auth";
import { getAccessToken } from "@/lib/auth/session";
import { useWebSocketChannel } from "@/lib/ws/use-websocket";
import { useNotificationsStore } from "@/stores/notifications-store";
import type { Notification } from "@/types/models";

/** Mounted once near the app root — streams the logged-in user's personal
 * notification channel for the lifetime of the session. Page-scoped data
 * (prices for a specific symbol list) is subscribed to by the pages that
 * need it, not here. */
export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const push = useNotificationsStore((s) => s.push);
  const token = user ? getAccessToken() : null;

  useWebSocketChannel<Notification>(
    `/ws/notifications?token=${token ?? ""}`,
    (message) => push(message),
    Boolean(user && token)
  );

  return <>{children}</>;
}
