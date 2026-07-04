import { apiGet, apiGetPaginated, apiPost } from "@/lib/api/client";
import type {
  Company,
  Fundamentals,
  NewsItem,
  Prediction,
  PriceBar,
  Recommendation,
  ResearchReport,
  SymbolMatch,
  Technicals,
} from "@/types/models";

export async function listCompanies(params: { search?: string; sector?: string; page?: number; size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.search) qs.set("search", params.search);
  if (params.sector) qs.set("sector", params.sector);
  qs.set("page", String(params.page ?? 1));
  qs.set("size", String(params.size ?? 20));
  return apiGetPaginated<Company[]>(`/api/v1/companies?${qs.toString()}`);
}

export async function getCompany(symbol: string): Promise<Company> {
  return apiGet<Company>(`/api/v1/companies/${symbol}`);
}

/** Live vendor search — finds any real NSE/BSE stock, tracked or not. */
export async function searchExternal(query: string): Promise<SymbolMatch[]> {
  return apiGet<SymbolMatch[]>(`/api/v1/companies/search/external?q=${encodeURIComponent(query)}`);
}

/** On-demand fetch for a symbol not yet tracked — real data, takes a few seconds. */
export async function trackCompany(symbol: string): Promise<Company> {
  return apiPost<Company>(`/api/v1/companies/${symbol}/track`);
}

export async function getPrices(symbol: string, interval = "1d"): Promise<PriceBar[]> {
  return apiGet<PriceBar[]>(`/api/v1/companies/${symbol}/prices?interval=${interval}`);
}

export async function getTechnicals(symbol: string, interval = "1d"): Promise<Technicals | null> {
  try {
    return await apiGet<Technicals>(`/api/v1/companies/${symbol}/technicals?interval=${interval}`);
  } catch {
    return null;
  }
}

export async function getFundamentals(symbol: string): Promise<Fundamentals[] | null> {
  try {
    return await apiGet<Fundamentals[]>(`/api/v1/companies/${symbol}/fundamentals`);
  } catch {
    return null;
  }
}

export async function getCompanyNews(symbol: string, page = 1) {
  return apiGetPaginated<NewsItem[]>(`/api/v1/companies/${symbol}/news?page=${page}`);
}

export async function getCompanyResearch(symbol: string): Promise<ResearchReport | null> {
  try {
    return await apiGet<ResearchReport>(`/api/v1/companies/${symbol}/research`);
  } catch {
    return null;
  }
}

export async function getCompanyRecommendation(symbol: string): Promise<Recommendation | null> {
  try {
    return await apiGet<Recommendation>(`/api/v1/companies/${symbol}/recommendation`);
  } catch {
    return null;
  }
}

export async function getCompanyPredictions(symbol: string): Promise<Prediction[]> {
  return apiGet<Prediction[]>(`/api/v1/companies/${symbol}/predictions`);
}

export async function getCompetitors(symbol: string): Promise<Company[]> {
  return apiGet<Company[]>(`/api/v1/companies/${symbol}/competitors`);
}
