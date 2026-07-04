import { apiGet } from "@/lib/api/client";
import type { MarketEvent, MarketOverview, Mover, SectorTrend } from "@/types/models";

export async function getMarketOverview(): Promise<MarketOverview | null> {
  return apiGet<MarketOverview | null>("/api/v1/markets/overview");
}

export async function getSectorTrends(): Promise<SectorTrend[]> {
  return apiGet<SectorTrend[]>("/api/v1/markets/sectors");
}

export async function getMovers(type: "gainers" | "losers", limit = 10): Promise<Mover[]> {
  return apiGet<Mover[]>(`/api/v1/markets/movers?type=${type}&limit=${limit}`);
}

export async function getMarketEvents(from: string, to: string): Promise<MarketEvent[]> {
  return apiGet<MarketEvent[]>(`/api/v1/markets/events?from=${from}&to=${to}`);
}
