import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api/client";
import type { Portfolio, PortfolioAnalytics } from "@/types/models";

export async function listPortfolios(): Promise<Portfolio[]> {
  return apiGet<Portfolio[]>("/api/v1/portfolios");
}

export async function createPortfolio(name: string, baseCurrency = "USD"): Promise<Portfolio> {
  return apiPost<Portfolio>("/api/v1/portfolios", { name, base_currency: baseCurrency });
}

export async function getPortfolio(id: string): Promise<Portfolio> {
  return apiGet<Portfolio>(`/api/v1/portfolios/${id}`);
}

export async function renamePortfolio(id: string, name: string): Promise<Portfolio> {
  return apiPatch<Portfolio>(`/api/v1/portfolios/${id}`, { name });
}

export async function deletePortfolio(id: string): Promise<void> {
  await apiDelete<void>(`/api/v1/portfolios/${id}`);
}

export async function recordTransaction(
  portfolioId: string,
  input: { symbol: string; side: "buy" | "sell"; quantity: string; price: string; fees?: string; note?: string }
): Promise<Portfolio> {
  return apiPost<Portfolio>(`/api/v1/portfolios/${portfolioId}/transactions`, input);
}

export async function getPortfolioAnalytics(id: string): Promise<PortfolioAnalytics> {
  return apiGet<PortfolioAnalytics>(`/api/v1/portfolios/${id}/analytics`);
}
