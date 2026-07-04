import { apiDelete, apiGet, apiPost } from "@/lib/api/client";
import type { Watchlist } from "@/types/models";

export async function listWatchlists(): Promise<Watchlist[]> {
  return apiGet<Watchlist[]>("/api/v1/watchlists");
}

export async function createWatchlist(name: string, isDefault = false): Promise<Watchlist> {
  return apiPost<Watchlist>("/api/v1/watchlists", { name, is_default: isDefault });
}

export async function deleteWatchlist(id: string): Promise<void> {
  await apiDelete<void>(`/api/v1/watchlists/${id}`);
}

export async function addWatchlistItem(watchlistId: string, symbol: string): Promise<Watchlist> {
  return apiPost<Watchlist>(`/api/v1/watchlists/${watchlistId}/items/${symbol}`);
}

export async function removeWatchlistItem(watchlistId: string, symbol: string): Promise<void> {
  await apiDelete<void>(`/api/v1/watchlists/${watchlistId}/items/${symbol}`);
}
