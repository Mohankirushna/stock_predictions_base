import { describe, expect, it } from "vitest";

import { ALERT_TYPES } from "@/lib/alert-types";

describe("ALERT_TYPES", () => {
  it("has a unique value for every entry", () => {
    const values = ALERT_TYPES.map((t) => t.value);
    expect(new Set(values).size).toBe(values.length);
  });

  it("gives every entry a non-empty label", () => {
    for (const t of ALERT_TYPES) {
      expect(t.label.length).toBeGreaterThan(0);
    }
  });
});
