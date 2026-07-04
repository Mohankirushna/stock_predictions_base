"use client";

import { AuthProvider } from "@/hooks/use-auth";
import { RealtimeProvider } from "@/components/providers/realtime-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <RealtimeProvider>{children}</RealtimeProvider>
    </AuthProvider>
  );
}
