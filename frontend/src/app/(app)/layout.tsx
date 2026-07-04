"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return <div className="flex h-screen items-center justify-center text-muted text-sm">Loading&hellip;</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="md:pl-56">
        <Topbar />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
