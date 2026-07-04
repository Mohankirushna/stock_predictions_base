"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  LineChart,
  Building2,
  Briefcase,
  FileSearch,
  Star,
  Bell,
  TrendingUp,
  Trophy,
  Settings,
  ShieldCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/markets", label: "Markets", icon: LineChart },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/research", label: "Research", icon: FileSearch },
  { href: "/watchlist", label: "Watchlist", icon: Star },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/predictions", label: "Predictions", icon: TrendingUp },
  { href: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r border-border bg-panel md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="size-2.5 rounded-full bg-accent" />
        <span className="text-sm font-semibold tracking-tight">Research Terminal</span>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-panel-hover text-foreground"
                  : "text-muted hover:bg-panel-hover hover:text-foreground"
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
        {user?.role === "admin" && (
          <Link
            href="/admin"
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              pathname.startsWith("/admin")
                ? "bg-panel-hover text-foreground"
                : "text-muted hover:bg-panel-hover hover:text-foreground"
            )}
          >
            <ShieldCheck className="size-4" />
            Admin
          </Link>
        )}
      </nav>
      <div className="border-t border-border p-3 text-[11px] leading-snug text-muted">
        Research guidance only. Never a trade order.
      </div>
    </aside>
  );
}
