/** In-memory access token, backed by sessionStorage so a page reload
 * doesn't force an immediate re-auth round trip. The refresh token itself
 * lives only in an httpOnly cookie the browser manages — this module never
 * touches it directly. */
const STORAGE_KEY = "access_token";

let accessToken: string | null = null;

function restore(): void {
  if (typeof window === "undefined") return;
  accessToken = window.sessionStorage.getItem(STORAGE_KEY);
}

if (typeof window !== "undefined") {
  restore();
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (typeof window === "undefined") return;
  if (token) {
    window.sessionStorage.setItem(STORAGE_KEY, token);
  } else {
    window.sessionStorage.removeItem(STORAGE_KEY);
  }
}

export function clearSession(): void {
  setAccessToken(null);
}
