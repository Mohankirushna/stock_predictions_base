import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreGauge } from "@/components/charts/score-gauge";

describe("ScoreGauge", () => {
  it("colors a score at the bull threshold (>=65) green", () => {
    render(<ScoreGauge score={65} />);
    expect(screen.getByText("65")).toHaveStyle({ color: "var(--bull)" });
  });

  it("colors a score at the bear threshold (<=35) red", () => {
    render(<ScoreGauge score={35} />);
    expect(screen.getByText("35")).toHaveStyle({ color: "var(--bear)" });
  });

  it("colors a mid-range score as a warning", () => {
    render(<ScoreGauge score={50} />);
    expect(screen.getByText("50")).toHaveStyle({ color: "var(--warning)" });
  });

  it("clamps and rounds out-of-range scores instead of rendering garbage", () => {
    render(<ScoreGauge score={142.6} />);
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("renders an optional label", () => {
    render(<ScoreGauge score={80} label="Score" />);
    expect(screen.getByText("Score")).toBeInTheDocument();
  });
});
