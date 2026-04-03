// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/components/similar-case-list", () => ({
  SimilarCaseList: ({
    currentChartWindow,
  }: {
    currentChartWindow: {
      highlight_range: {
        start_date: string;
        end_date: string;
      };
    } | null;
  }) => (
    <div>
      <span data-testid="current-highlight-start">{currentChartWindow?.highlight_range.start_date ?? "none"}</span>
      <span data-testid="current-highlight-end">{currentChartWindow?.highlight_range.end_date ?? "none"}</span>
    </div>
  ),
}));

import { PredictionPanel } from "../src/components/prediction-panel";

describe("prediction panel query window", () => {
  afterEach(() => cleanup());

  it("uses the backend query window as the current comparison highlight", () => {
    render(
      <PredictionPanel
        apiClient={{ getSegmentChartWindow: vi.fn() }}
        stockCode="600010"
        prices={[
          { trade_date: "2026-03-10", open_price: 2.2, high_price: 2.25, low_price: 2.18, close_price: 2.21, volume: 120000 },
          { trade_date: "2026-03-11", open_price: 2.21, high_price: 2.23, low_price: 2.11, close_price: 2.14, volume: 125000 },
          { trade_date: "2026-03-12", open_price: 2.14, high_price: 2.16, low_price: 2.05, close_price: 2.08, volume: 130000 },
          { trade_date: "2026-03-13", open_price: 2.08, high_price: 2.1, low_price: 2.0, close_price: 2.03, volume: 135000 },
          { trade_date: "2026-03-16", open_price: 2.03, high_price: 2.04, low_price: 1.96, close_price: 1.99, volume: 140000 },
          { trade_date: "2026-03-17", open_price: 1.99, high_price: 2.0, low_price: 1.92, close_price: 1.95, volume: 145000 },
          { trade_date: "2026-03-18", open_price: 1.95, high_price: 1.98, low_price: 1.9, close_price: 1.93, volume: 150000 },
          { trade_date: "2026-03-19", open_price: 1.93, high_price: 1.96, low_price: 1.88, close_price: 1.9, volume: 155000 },
          { trade_date: "2026-03-20", open_price: 1.9, high_price: 1.92, low_price: 1.84, close_price: 1.87, volume: 160000 },
          { trade_date: "2026-03-23", open_price: 1.87, high_price: 1.88, low_price: 1.8, close_price: 1.82, volume: 165000 },
          { trade_date: "2026-03-24", open_price: 1.82, high_price: 1.84, low_price: 1.78, close_price: 1.8, volume: 170000 },
        ]}
        autoPoints={[]}
        finalPoints={[
          { point_date: "2026-03-10", point_type: "peak", point_price: 2.21, source_type: "system" },
          { point_date: "2026-03-24", point_type: "trough", point_price: 1.8, source_type: "system" },
        ]}
        currentState={{
          label: "底部构建中",
          summary: "desc",
          probabilities: {},
          key_features: {},
          risk_flags: {},
          similar_cases: [],
          query_window: {
            start_date: "2026-03-12",
            end_date: "2026-03-20",
            window_size: 7,
          },
        }}
      />
    );

    expect(screen.getByTestId("current-highlight-start").textContent).toBe("2026-03-12");
    expect(screen.getByTestId("current-highlight-end").textContent).toBe("2026-03-20");
  });
});
