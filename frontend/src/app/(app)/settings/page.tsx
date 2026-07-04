"use client";

import Link from "next/link";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <div>
      <PageHeader title="Settings" description="Profile, theme, and notification preferences." />

      <div className="max-w-xl space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex size-12 items-center justify-center rounded-full bg-panel-hover text-lg font-bold text-accent">
                {(user?.full_name || user?.email || "?").slice(0, 1).toUpperCase()}
              </div>
              <div>
                <p className="font-medium">{user?.full_name || "Unnamed user"}</p>
                <p className="text-sm text-muted">{user?.email}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={user?.role === "admin" ? "accent" : "default"}>{user?.role}</Badge>
              <Badge variant="outline">{user?.auth_provider}</Badge>
              <Badge variant={user?.email_verified ? "bull" : "warning"}>
                {user?.email_verified ? "Email verified" : "Email not verified"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted">
            <p>
              Research Terminal currently ships with a single dark theme, and notification preferences are managed
              per-alert from the <Link href="/alerts" className="text-accent hover:underline">Alerts</Link> page.
            </p>
          </CardContent>
        </Card>

        {user?.role === "admin" && (
          <Card>
            <CardHeader>
              <CardTitle>Administration</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted">
              <p className="mb-3">
                You have admin access to AI provider configuration, score weights, spend tracking, and the agent
                console.
              </p>
              <Link href="/admin">
                <Button size="sm" variant="outline">
                  Open Admin Console
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="destructive" size="sm" onClick={() => void logout()}>
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
