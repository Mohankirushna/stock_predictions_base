import { apiGet, apiPost } from "@/lib/api/client";
import { setAccessToken } from "@/lib/auth/session";
import type { User } from "@/types/models";

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function register(email: string, password: string, fullName?: string): Promise<User> {
  const res = await apiPost<AuthResponse>("/api/v1/auth/register", {
    email,
    password,
    full_name: fullName ?? "",
  });
  setAccessToken(res.access_token);
  return res.user;
}

export async function login(email: string, password: string): Promise<User> {
  const res = await apiPost<AuthResponse>("/api/v1/auth/login", { email, password });
  setAccessToken(res.access_token);
  return res.user;
}

export async function logout(): Promise<void> {
  await apiPost<void>("/api/v1/auth/logout");
  setAccessToken(null);
}

export async function me(): Promise<User> {
  return apiGet<User>("/api/v1/auth/me");
}

export function googleLoginUrl(apiBase: string): string {
  return `${apiBase}/api/v1/auth/google`;
}
