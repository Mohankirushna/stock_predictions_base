import type { Fundamentals } from "@/types/models";

const ROWS: { label: string; key: keyof Fundamentals; suffix?: string }[] = [
  { label: "Revenue", key: "revenue" },
  { label: "Revenue Growth YoY", key: "revenue_growth_yoy", suffix: "%" },
  { label: "Net Income", key: "net_income" },
  { label: "EPS", key: "eps" },
  { label: "EPS Growth YoY", key: "eps_growth_yoy", suffix: "%" },
  { label: "Gross Margin", key: "gross_margin", suffix: "%" },
  { label: "Operating Margin", key: "operating_margin", suffix: "%" },
  { label: "Net Margin", key: "net_margin", suffix: "%" },
  { label: "Free Cash Flow", key: "free_cash_flow" },
  { label: "Operating Cash Flow", key: "operating_cash_flow" },
  { label: "Total Debt", key: "total_debt" },
  { label: "Debt / Equity", key: "debt_to_equity" },
  { label: "ROE", key: "roe", suffix: "%" },
  { label: "ROA", key: "roa", suffix: "%" },
  { label: "P/E", key: "pe" },
  { label: "PEG", key: "peg" },
  { label: "Institutional Ownership", key: "institutional_ownership_pct", suffix: "%" },
  { label: "Dividend Yield", key: "dividend_yield", suffix: "%" },
  { label: "Dividend Payout Ratio", key: "dividend_payout_ratio", suffix: "%" },
];

export function FundamentalsTab({ snapshots }: { snapshots: Fundamentals[] | null }) {
  if (!snapshots || snapshots.length === 0) {
    return <p className="text-sm text-muted">No fundamental data available for this company yet.</p>;
  }
  const latest = snapshots[0];

  return (
    <div>
      <p className="mb-3 text-xs text-muted">
        {latest.period.toUpperCase()} &middot; fiscal date {latest.fiscal_date}
      </p>
      <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
        {ROWS.map(({ label, key, suffix }) => {
          const value = latest[key];
          return (
            <div key={key} className="flex items-center justify-between border-b border-border py-1.5 text-sm last:border-0">
              <span className="text-muted">{label}</span>
              <span className="font-mono font-medium">{value !== null ? `${value}${suffix ?? ""}` : "—"}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
