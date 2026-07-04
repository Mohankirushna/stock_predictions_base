import { apiGet } from "@/lib/api/client";
import type { LeaderboardEntry } from "@/types/models";

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  return apiGet<LeaderboardEntry[]>("/api/v1/predictions/leaderboard");
}
