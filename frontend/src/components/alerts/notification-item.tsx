import { cn } from "@/lib/utils";
import type { Notification } from "@/types/models";

export function NotificationItem({ notification }: { notification: Notification }) {
  const unread = !notification.read_at;
  return (
    <div className={cn("flex items-start gap-2 rounded-md p-3 text-sm", unread && "bg-panel-hover")}>
      <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", unread ? "bg-accent" : "bg-transparent")} />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{notification.title}</p>
        <p className="text-muted">{notification.body}</p>
        <p className="mt-1 text-[11px] text-muted">{new Date(notification.created_at).toLocaleString()}</p>
      </div>
    </div>
  );
}
