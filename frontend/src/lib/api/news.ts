import { apiGet } from "@/lib/api/client";
import type { NewsItem } from "@/types/models";

export async function getTrendingNews(limit = 20): Promise<NewsItem[]> {
  return apiGet<NewsItem[]>(`/api/v1/news/trending?limit=${limit}`);
}
