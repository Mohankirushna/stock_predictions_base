"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";

export default function RootPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (isLoading) return;
    router.replace(user ? "/dashboard" : "/login");
  }, [user, isLoading, router]);

  return (
    <div className="flex h-screen items-center justify-center text-muted text-sm">
      Loading&hellip;
    </div>
  );
}
