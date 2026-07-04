import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChangeBadge } from "@/components/dashboard/change-badge";

describe("ChangeBadge", () => {
  it("shows a plus sign for a positive change", () => {
    render(<ChangeBadge value={1.68} />);
    expect(screen.getByText("+1.68%")).toBeInTheDocument();
  });

  it("shows a minus sign — not a plus sign — for a negative change", () => {
    // Regression: formatPct(Math.abs(num)) previously stripped the sign
    // before formatting, so losers rendered with a down arrow next to "+0.90%".
    render(<ChangeBadge value={-0.9} />);
    expect(screen.getByText("-0.90%")).toBeInTheDocument();
    expect(screen.queryByText("+0.90%")).not.toBeInTheDocument();
  });

  it("accepts a numeric string", () => {
    render(<ChangeBadge value="-2.5" />);
    expect(screen.getByText("-2.50%")).toBeInTheDocument();
  });
});
