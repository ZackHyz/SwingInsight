// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
      label: "主升初期",
      summary: "量价共振，延续概率较高",
      probabilities: {
        up_1d: 0.64,
        flat_1d: 0.2,
        down_1d: 0.16,
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
          price_score: 0.88,
          candle_score: 0.93,
          volume_score: 0.74,
          turnover_score: 0.66,
          trend_score: 0.71,
          vola_score: 0.69,
          pct_change: 22.5,
          return_1d: 0.012,
          return_3d: 0.034,
          return_5d: -0.028,
          return_10d: 0.086,
          start_date: "2024-02-01",
          end_date: "2024-02-20",
          window_id: 21,
          window_start_date: "2024-02-05",
          window_end_date: "2024-02-13",
          window_size: 7,
          segment_start_date: "2024-02-01",
          segment_end_date: "2024-02-20",
        },
      ],
      group_stat: {
        sample_count: 20,
        future_1d_mean: -0.0182,
        future_1d_median: -0.011,
        future_1d_win_rate: 0.35,
        future_3d_mean: -0.0355,
        future_5d_mean: -0.0476,
        future_10d_mean: 0.0091,
        future_5d_max_dd_median: -0.064,
        future_10d_max_dd_median: -0.082,
      },
    },
  };
}

describe("prediction panel", () => {
  afterEach(() => cleanup());

  it("renders state, probabilities, and similar cases", async () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn().mockResolvedValue({
        segment: { id: 12, stock_code: "000001", start_date: "2024-02-01", end_date: "2024-02-20" },
        highlight_range: { start_date: "2024-02-05", end_date: "2024-02-13" },
        prices: [
          { trade_date: "2024-02-01", open_price: 10.1, high_price: 10.4, low_price: 9.9, close_price: 10.2, volume: 10000 },
          { trade_date: "2024-02-05", open_price: 10.2, high_price: 10.6, low_price: 10.1, close_price: 10.5, volume: 12000 },
          { trade_date: "2024-02-13", open_price: 10.5, high_price: 10.8, low_price: 10.4, close_price: 10.6, volume: 14000 },
        ],
        auto_turning_points: [{ point_date: "2024-02-05", point_type: "trough", point_price: 10.1, source_type: "system" }],
        final_turning_points: [{ point_date: "2024-02-13", point_type: "peak", point_price: 10.8, source_type: "manual" }],
      }),
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

    expect(screen.getByText("Intelligence Rail")).toBeTruthy();
    const panel = screen.getByRole("heading", { name: "预测面板" }).closest("aside");
    expect(panel).toBeTruthy();
    const scoped = within(panel as HTMLElement);
    const items = scoped.getAllByRole("listitem");

    expect(scoped.getByText("当前状态: 主升初期")).toBeTruthy();
    expect(scoped.getByText("相似样本时间线")).toBeTruthy();
    expect(scoped.getByText(/按排序模式输出的历史窗口列表/)).toBeTruthy();
    expect(panel?.textContent).toContain("相似样本数 20");
    expect(panel?.textContent).toContain("1日均值 -1.82%");
    expect(panel?.textContent).toContain("1日胜率 35.0%");
    expect(panel?.textContent).toContain("5日均值 -4.76%");
    expect(panel?.textContent).toContain("10日均值 +0.91%");
    expect(items.at(-1)?.textContent).toContain("窗口日期 2024-02-05 至 2024-02-13 · 相似度 91.0%");
    expect(items.at(-1)?.textContent).toContain("5日 -2.80% · 10日 +8.60%");
    expect(items.at(-1)?.textContent).toContain("20日");
    expect(items.at(-1)?.textContent).toContain("同标的");
    expect(items.at(-1)?.textContent).toContain("样本股票 000001 · 波段ID 12");
    expect(panel?.textContent).toContain("次日上涨 64.0%");
    expect(panel?.textContent).toContain("次日震荡 20.0%");
    expect(panel?.textContent).toContain("10日上涨 58.0%");
    expect(panel?.textContent).toContain("5日震荡 23.0%");
    expect(panel?.textContent).toContain("量比(5日) 1.4");
    expect(panel?.textContent).toContain("正向新闻占比 0.75");
    expect(scoped.getByText("回撤风险: 低")).toBeTruthy();
    expect(scoped.getByRole("heading", { name: "排序模式" })).toBeTruthy();
    fireEvent.change(scoped.getByLabelText("排序模式"), { target: { value: "similarity_first" } });
    fireEvent.click(scoped.getByRole("button", { name: "已选中" }));
    await waitFor(() => {
      expect(scoped.getByText("样本对比视图")).toBeTruthy();
    });
    expect(screen.getByText("历史买卖点占位: 1")).toBeTruthy();
    expect(screen.getByText("Liquidity support boosts banks")).toBeTruthy();
  });
});
