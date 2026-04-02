// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import StockResearchPage from "../src/app/stocks/[stockCode]/page";
import type { ApiClient, StockResearchData, TurningPointCommitPayload, TurningPointCommitResponse } from "../src/lib/api";

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
      { trade_date: "2024-01-05", close_price: 9.7, high_price: 9.9, low_price: 8.9, open_price: 8.9 },
    ],
    auto_turning_points: [
      { id: 1, point_date: "2024-01-04", point_type: "trough", point_price: 8.8, source_type: "system" },
    ],
    final_turning_points: [
      { id: 11, point_date: "2024-01-04", point_type: "trough", point_price: 8.8, source_type: "manual" },
    ],
    trade_markers: [
      {
        trade_date: "2024-01-03",
        trade_type: "buy",
        price: 9.4,
      },
    ],
    news_items: [
      {
        news_id: 7,
        title: "Liquidity support boosts banks",
        summary: "Positive catalyst near the rebound",
        source_name: "wire",
        news_date: "2024-01-03",
      },
    ],
    current_state: {
      label: "placeholder",
      summary: "Prediction pending",
    },
  };
}

describe("turning point editor", () => {
  afterEach(() => {
    cleanup();
  });

  it("lets the user select trough mode, click the chart, and save edits", async () => {
    const commit = vi
      .fn<(stockCode: string, payload: TurningPointCommitPayload) => Promise<TurningPointCommitResponse>>()
      .mockResolvedValue({
        auto_turning_points: [
          { id: 1, point_date: "2024-01-04", point_type: "trough", point_price: 8.8, source_type: "system" },
          { id: 2, point_date: "2024-01-05", point_type: "peak", point_price: 9.9, source_type: "system" },
        ],
        final_turning_points: [
          { id: 21, point_date: "2024-01-03", point_type: "trough", point_price: 9.4, source_type: "manual" },
          { id: 22, point_date: "2024-01-05", point_type: "peak", point_price: 9.9, source_type: "system" },
        ],
        rebuild_summary: { segments: 1, features: 8, predictions: 1, version_code: "manual:latest" },
        current_state: {
          label: "主升初期",
          summary: "主升初期，10日上行概率 0.58",
          probabilities: { up_10d: 0.58 },
          key_features: { volume_ratio_5d: 1.4 },
          risk_flags: { pullback_risk: "low" },
          similar_cases: [],
        },
      });
    const apiClient: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: commit,
      getSegmentChartWindow: vi.fn(),
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

    fireEvent.click(screen.getByRole("button", { name: "标记波谷" }));
    fireEvent.click(screen.getByTestId("kline-canvas"), { clientX: 120, clientY: 140 });
    fireEvent.click(screen.getByRole("button", { name: "保存修正" }));

    await waitFor(() => {
      expect(commit).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText("保存成功")).toBeTruthy();
    expect(screen.getByText("重算完成: 1 个波段 / 8 个特征 / 1 条预测")).toBeTruthy();
  });

  it("lets the user select, move, and delete a final point", () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
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

    fireEvent.click(screen.getByRole("button", { name: "选择 2024-01-04 trough" }));
    fireEvent.click(screen.getByRole("button", { name: "标记波峰" }));
    fireEvent.click(screen.getByTestId("kline-canvas"), { clientX: 0, clientY: 100 });

    expect(screen.getByText("2024-01-02 peak 10.2")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "选择 2024-01-02 peak" }));
    fireEvent.click(screen.getByRole("button", { name: "删除选中点" }));

    expect(screen.queryByText("2024-01-02 peak 10.2")).toBeNull();
  });
});
