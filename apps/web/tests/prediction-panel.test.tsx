// @vitest-environment jsdom

import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import StockResearchPage from "../src/app/stocks/[stockCode]/page";
import type { ApiClient, StockResearchData } from "../src/lib/api";

function buildData(): StockResearchData {
  return {
    stock: {
      stock_code: "000001",
      stock_name: "Ping An Bank",
      market: "A",
      industry: "Bank",
      concept_tags: ["finance"],
    },
    prices: [
      { trade_date: "2024-01-02", close_price: 10.0, high_price: 10.2, low_price: 9.8, open_price: 10.0 },
      { trade_date: "2024-01-03", close_price: 9.4, high_price: 9.9, low_price: 9.2, open_price: 9.8 },
      { trade_date: "2024-01-04", close_price: 8.8, high_price: 9.3, low_price: 8.7, open_price: 9.2 },
    ],
    auto_turning_points: [],
    final_turning_points: [],
    trade_markers: [],
    current_state: {
      label: "主升初期",
      summary: "量价共振，延续概率较高",
      probabilities: {
        up_5d: 0.62,
        flat_5d: 0.23,
        down_5d: 0.15,
        up_10d: 0.58,
        flat_10d: 0.22,
        down_10d: 0.2,
        up_20d: 0.49,
        flat_20d: 0.25,
        down_20d: 0.26,
      },
      key_features: {
        volume_ratio_5d: 1.4,
        positive_news_ratio: 0.75,
      },
      risk_flags: {
        pullback_risk: "low",
      },
      similar_cases: [
        {
          segment_id: 12,
          stock_code: "000001",
          score: 0.91,
          pct_change: 22.5,
        },
      ],
    },
  };
}

describe("prediction panel", () => {
  afterEach(() => cleanup());

  it("renders state, probabilities, and similar cases", () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
    };

    render(
      <StockResearchPage
        stockCode="000001"
        initialData={buildData()}
        apiClient={apiClient}
      />
    );

    const panel = screen.getByRole("heading", { name: "预测面板" }).closest("aside");
    expect(panel).toBeTruthy();
    const scoped = within(panel as HTMLElement);
    const items = scoped.getAllByRole("listitem");

    expect(scoped.getByText("当前状态: 主升初期")).toBeTruthy();
    expect(scoped.getByText("相似历史样本")).toBeTruthy();
    expect(items.at(-1)?.textContent).toContain("000001 0.91 22.50");
    expect(scoped.getByText("up_10d 58.0%")).toBeTruthy();
  });
});
