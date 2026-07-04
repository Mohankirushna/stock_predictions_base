import { clearSession, getAccessToken, setAccessToken } from "@/lib/auth/session";
import type { Envelope } from "@/types/api";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipAuthRetry?: boolean;
}

async function rawRequest<T>(path: string, options: RequestOptions = {}): Promise<Envelope<T>> {
  const { body, skipAuthRetry, headers, ...rest } = options;
  const token = getAccessToken();

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const status = response.status;
  const envelope: Envelope<T> =
    status === 204 ? { data: null, meta: null, error: null } : await response.json();

  if (!response.ok) {
    if (status === 401 && !skipAuthRetry && path !== "/api/v1/auth/refresh") {
      const refreshed = await tryRefresh();
      if (refreshed) {
        return rawRequest<T>(path, { ...options, skipAuthRetry: true });
      }
      clearSession();
    }
    const err = envelope.error;
    throw new ApiRequestError(err?.message ?? "Request failed", err?.code ?? "unknown_error", status, err?.details);
  }

  return envelope;
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!resp.ok) return false;
        const envelope = await resp.json();
        const token = envelope?.data?.access_token as string | undefined;
        if (!token) return false;
        setAccessToken(token);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiGet<T>(path: string, options?: RequestOptions): Promise<T> {
  const envelope = await rawRequest<T>(path, { ...options, method: "GET" });
  return envelope.data as T;
}

export async function apiPost<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  const envelope = await rawRequest<T>(path, { ...options, method: "POST", body });
  return envelope.data as T;
}

export async function apiPatch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  const envelope = await rawRequest<T>(path, { ...options, method: "PATCH", body });
  return envelope.data as T;
}

export async function apiDelete<T>(path: string, options?: RequestOptions): Promise<T> {
  const envelope = await rawRequest<T>(path, { ...options, method: "DELETE" });
  return envelope.data as T;
}

export async function apiGetPaginated<T>(
  path: string,
  options?: RequestOptions
): Promise<{ data: T; meta: { page: number; size: number; total: number } }> {
  const envelope = await rawRequest<T>(path, { ...options, method: "GET" });
  return { data: envelope.data as T, meta: envelope.meta as { page: number; size: number; total: number } };
}
