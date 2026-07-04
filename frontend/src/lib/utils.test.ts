import { describe, expect, it } from "vitest";

import { cn, formatCompactNumber, formatCurrency, formatPct } from "@/lib/utils";

describe("formatCurrency", () => {
  it("formats a positive number as INR by default", () => {
    expect(formatCurrency(1234.5)).toBe("₹1,234.50");
  });

  it("accepts string input", () => {
    expect(formatCurrency("99.9")).toBe("₹99.90");
  });

  it("uses Indian digit grouping for INR", () => {
    expect(formatCurrency(123456.789)).toBe("₹1,23,456.79");
  });

  it("respects a custom currency", () => {
    expect(formatCurrency(10, "EUR")).toBe("€10.00");
  });

  it("uses US grouping for USD", () => {
    expect(formatCurrency(123456.789, "USD")).toBe("$123,456.79");
  });
});

describe("formatPct", () => {
  it("prefixes positive values with a plus sign", () => {
    expect(formatPct(1.68)).toBe("+1.68%");
  });

  it("does not double up a minus sign for negative values", () => {
    expect(formatPct(-0.9)).toBe("-0.90%");
  });

  it("adds no sign for exactly zero", () => {
    expect(formatPct(0)).toBe("0.00%");
  });
});

describe("formatCompactNumber", () => {
  it("compacts large numbers", () => {
    expect(formatCompactNumber(18_500_000_000)).toBe("18.5B");
  });
});

describe("cn", () => {
  it("merges tailwind class conflicts, keeping the last one", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });

  it("drops falsy values", () => {
    expect(cn("a", false, undefined, "b")).toBe("a b");
  });
});
