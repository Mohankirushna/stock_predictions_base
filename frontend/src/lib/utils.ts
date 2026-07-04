import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// This platform tracks NSE/BSE (Indian) stocks exclusively, so INR is the
// correct default whenever a caller doesn't have a specific currency handy —
// only genuinely global figures (macro proxies like Oil/Gold/BTC) are USD.
const LOCALE_BY_CURRENCY: Record<string, string> = { INR: "en-IN", USD: "en-US" };

export function formatCurrency(value: number | string, currency = "INR"): string {
  const num = typeof value === "string" ? Number(value) : value;
  const locale = LOCALE_BY_CURRENCY[currency] ?? "en-US";
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(num);
}

export function formatPct(value: number | string, digits = 2): string {
  const num = typeof value === "string" ? Number(value) : value;
  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toFixed(digits)}%`;
}

export function formatCompactNumber(value: number | string): string {
  const num = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(num);
}
