"use client";

import Link from "next/link";
import { Bell, LogOut, User as UserIcon } from "lucide-react";

import { useAuth } from "@/hooks/use-auth";
import { useNotificationsStore } from "@/stores/notifications-store";
import { CommandPalette } from "@/components/layout/command-palette";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Topbar() {
  const { user, logout } = useAuth();
  const unreadCount = useNotificationsStore((s) => s.unreadCount);

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur">
      <CommandPalette />
      <div className="ml-auto flex items-center gap-3">
        <Link href="/alerts" className="relative flex size-8 items-center justify-center rounded-md hover:bg-panel-hover">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <Badge variant="accent" className="absolute -right-1 -top-1 h-4 min-w-4 justify-center px-1 text-[10px]">
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </Link>
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-panel-hover">
            <UserIcon className="size-4" />
            <span className="max-w-[10rem] truncate">{user?.full_name || user?.email}</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href="/settings">Settings</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => logout()} className="text-bear">
              <LogOut className="mr-2 size-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
