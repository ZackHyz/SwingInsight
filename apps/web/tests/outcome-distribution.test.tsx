// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { OutcomeDistribution } from "../src/components/outcome-distribution";

describe("outcome distribution", () => {
  afterEach(() => cleanup());

  it("renders loading and empty states", () => {
    render(<OutcomeDistribution groupStat={null} loading />);
    expect(screen.getByText("正在加载分布数据...")).toBeTruthy();

    cleanup();
    render(<OutcomeDistribution groupStat={null} />);
    expect(screen.getByText("暂无可用分布数据。")).toBeTruthy();
  });

  it("renders histogram rows from active horizon distribution", () => {
    render(
      <OutcomeDistribution
        groupStat={{
          horizon_days: [5, 10, 20],
          win_rates: [0.5, 0.6, 0.7],
          avg_returns: [0.01, 0.018, 0.03],
          sample_counts: [10, 10, 10],
          return_distribution: [-0.031, -0.011, 0.004, 0.027, 0.041],
          return_distributions: {
            "5": [-0.031, -0.011, 0.004],
            "10": [-0.031, -0.011, 0.004, 0.027, 0.041],
            "20": [-0.06, -0.02, 0.08],
          },
        }}
      />
    );

    expect(screen.getByText("结果分布")).toBeTruthy();
    expect(screen.getByText(/10日后涨跌分布/)).toBeTruthy();
    expect(screen.getByText("当前预测落点: +1.8%")).toBeTruthy();
    expect(screen.getByText("-4.0% ~ -2.0%")).toBeTruthy();
    expect(screen.getByText("-2.0% ~ +0.0%")).toBeTruthy();
    expect(screen.getByText("+0.0% ~ +2.0%")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "20d" }));
    expect(screen.getByText(/20日后涨跌分布/)).toBeTruthy();
  });

  it("highlights selected case return bucket by horizon", () => {
    render(
      <OutcomeDistribution
        selectedReturnsByHorizon={{ 10: 0.027 }}
        groupStat={{
          horizon_days: [5, 10, 20],
          win_rates: [0.5, 0.6, 0.7],
          avg_returns: [0.01, 0.02, 0.03],
          sample_counts: [10, 10, 10],
          return_distribution: [-0.031, -0.011, 0.004, 0.027, 0.041],
          return_distributions: {
            "10": [-0.031, -0.011, 0.004, 0.027, 0.041],
          },
        }}
      />
    );

    expect(screen.getByText((content) => content.includes("●"))).toBeTruthy();
  });
});
