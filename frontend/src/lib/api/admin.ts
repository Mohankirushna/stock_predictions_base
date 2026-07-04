import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type { AdminSettings, AdminStats, AIUsageEntry } from "@/types/models";

export async function getAdminStats(): Promise<AdminStats> {
  return apiGet<AdminStats>("/api/v1/admin/stats");
}

export async function getAiUsage(params: { provider?: string; from?: string } = {}): Promise<AIUsageEntry[]> {
  const qs = new URLSearchParams();
  if (params.provider) qs.set("provider", params.provider);
  if (params.from) qs.set("from", params.from);
  return apiGet<AIUsageEntry[]>(`/api/v1/admin/ai-usage?${qs.toString()}`);
}

export async function runAgent(name: string): Promise<{ task_id: string; agent: string }> {
  return apiPost<{ task_id: string; agent: string }>(`/api/v1/admin/agents/${name}/run`);
}

export async function getAdminSettings(): Promise<AdminSettings> {
  return apiGet<AdminSettings>("/api/v1/admin/settings");
}

export async function updateAdminSettings(scoreWeights: Record<string, number>): Promise<AdminSettings> {
  return apiPatch<AdminSettings>("/api/v1/admin/settings", { score_weights: scoreWeights });
}
