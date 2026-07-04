import { apiGet, apiGetPaginated, apiPost } from "@/lib/api/client";
import type { Opportunity, Recommendation } from "@/types/models";

export async function listOpportunities(): Promise<Opportunity[]> {
  return apiGet<Opportunity[]>("/api/v1/research/opportunities");
}

export async function generateReport(symbol: string): Promise<{ task_id: string; symbol: string }> {
  return apiPost<{ task_id: string; symbol: string }>(`/api/v1/research/reports/${symbol}/generate`);
}

export async function getTaskStatus(taskId: string): Promise<{ task_id: string; status: string }> {
  return apiGet(`/api/v1/research/tasks/${taskId}`);
}

export async function screenRecommendations(params: { minScore?: number; sector?: string; page?: number } = {}) {
  const qs = new URLSearchParams();
  qs.set("min_score", String(params.minScore ?? 0));
  if (params.sector) qs.set("sector", params.sector);
  qs.set("page", String(params.page ?? 1));
  return apiGetPaginated<Recommendation[]>(`/api/v1/recommendations?${qs.toString()}`);
}
