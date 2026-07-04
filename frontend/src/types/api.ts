/** Mirrors the backend's response envelope (backend/app/api/v1/envelope.py). */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface PageMeta {
  page: number;
  size: number;
  total: number;
}

export interface Envelope<T> {
  data: T | null;
  meta: PageMeta | Record<string, unknown> | null;
  error: ApiError | null;
}
