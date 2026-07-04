import { beforeEach, describe, expect, it } from "vitest";

import { clearSession, getAccessToken, setAccessToken } from "@/lib/auth/session";

describe("session token storage", () => {
  beforeEach(() => {
    clearSession();
  });

  it("returns null before any token is set", () => {
    expect(getAccessToken()).toBeNull();
  });

  it("round-trips a token through sessionStorage", () => {
    setAccessToken("abc.def.ghi");
    expect(getAccessToken()).toBe("abc.def.ghi");
    expect(window.sessionStorage.getItem("access_token")).toBe("abc.def.ghi");
  });

  it("clearSession removes the token from memory and storage", () => {
    setAccessToken("abc.def.ghi");
    clearSession();
    expect(getAccessToken()).toBeNull();
    expect(window.sessionStorage.getItem("access_token")).toBeNull();
  });
});
