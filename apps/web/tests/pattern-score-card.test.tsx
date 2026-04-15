// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PatternScoreCard } from "../src/components/pattern-score-card";

describe("pattern score card", () => {
  afterEach(() => cleanup());

  it("renders loading state", () => {
    render(<PatternScoreCard score={null} loading />);
    expect(screen.getByText("正在计算相似形态历史统计...")).toBeTruthy();
  });

  it("renders score metrics", () => {
    render(
      <PatternScoreCard
        score={{
          horizon_days: 10,
          raw_win_rate: 0.67,
          win_rate_5d: 0.5934,
          win_rate_10d: 0.5712,
          win_rate: 0.67,
          avg_return: 0.043,
          sample_count: 12,
          confidence: "medium",
          calibrated: true,
        }}
      />
    );
    expect(screen.getByText("5日胜率 59.3%")).toBeTruthy();
    expect(screen.getByText("10日胜率 57.1%")).toBeTruthy();
    expect(screen.getByText("10日预期涨跌")).toBeTruthy();
    expect(screen.getByText("+4.30%")).toBeTruthy();
    expect(screen.getByText("原始胜率 67.0%")).toBeTruthy();
    expect(screen.getByText("样本数 n=12")).toBeTruthy();
    expect(screen.getByText("置信度 中置信度")).toBeTruthy();
    expect(screen.getByText("概率校准 已启用(Platt)")).toBeTruthy();
  });
});
