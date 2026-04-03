// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SimilarCaseList } from "../src/components/similar-case-list";

function buildChartWindow(segmentId: number) {
  return {
    segment: {
      id: segmentId,
      stock_code: segmentId === 12 ? "600157" : "600010",
      start_date: "2025-08-01",
      end_date: "2025-09-12",
    },
    highlight_range: {
      start_date: "2025-08-01",
      end_date: "2025-09-12",
    },
    prices: [
      { trade_date: "2025-07-18", open_price: 5.1, high_price: 5.4, low_price: 4.9, close_price: 5.3, volume: 100000 },
      { trade_date: "2025-08-01", open_price: 5.3, high_price: 5.5, low_price: 5.0, close_price: 5.1, volume: 80000 },
      { trade_date: "2025-09-12", open_price: 5.1, high_price: 5.6, low_price: 5.0, close_price: 5.5, volume: 140000 },
      { trade_date: "2025-09-26", open_price: 5.5, high_price: 5.8, low_price: 5.4, close_price: 5.7, volume: 160000 },
    ],
    auto_turning_points: [{ point_date: "2025-09-12", point_type: "peak", point_price: 5.6, source_type: "system" }],
    final_turning_points: [{ point_date: "2025-08-01", point_type: "trough", point_price: 5.0, source_type: "manual" }],
  };
}

function buildCurrentChartWindow() {
  return {
    segment: {
      id: 0,
      stock_code: "600010",
      start_date: "2026-03-02",
      end_date: "2026-04-01",
    },
    highlight_range: {
      start_date: "2026-03-02",
      end_date: "2026-04-01",
    },
    prices: [
      { trade_date: "2026-02-16", open_price: 2.1, high_price: 2.2, low_price: 2.0, close_price: 2.15, volume: 120000 },
      { trade_date: "2026-03-02", open_price: 2.15, high_price: 2.16, low_price: 2.0, close_price: 2.01, volume: 180000 },
      { trade_date: "2026-03-12", open_price: 2.0, high_price: 2.1, low_price: 1.9, close_price: 1.98, volume: 220000 },
      { trade_date: "2026-04-01", open_price: 1.82, high_price: 1.86, low_price: 1.81, close_price: 1.84, volume: 140000 },
    ],
    auto_turning_points: [{ point_date: "2026-03-12", point_type: "peak", point_price: 2.1, source_type: "system" }],
    final_turning_points: [{ point_date: "2026-03-02", point_type: "peak", point_price: 2.01, source_type: "system" }],
  };
}

describe("similar case list", () => {
  afterEach(() => cleanup());

  it("renders readable chinese explanation for similar cases", () => {
    const loadSegmentChartWindow = vi.fn();
    render(
      <SimilarCaseList
        currentChartWindow={buildCurrentChartWindow()}
        loadSegmentChartWindow={loadSegmentChartWindow}
        items={[
          {
            segment_id: 12,
            stock_code: "600157",
            score: 0.8342,
            price_score: 0.781,
            volume_score: 0.864,
            turnover_score: 0.742,
            pattern_score: 0.901,
            candle_score: 0.901,
            trend_score: 0.688,
            vola_score: 0.744,
            pct_change: 12.36,
            return_1d: 0.015,
            return_3d: -0.022,
            return_5d: 0.048,
            return_10d: 0.126,
            start_date: "2025-08-01",
            end_date: "2025-09-12",
            window_id: 301,
            window_start_date: "2025-08-01",
            window_end_date: "2025-08-07",
            window_size: 7,
            segment_start_date: "2025-08-01",
            segment_end_date: "2025-09-12",
          },
        ]}
      />
    );

    expect(screen.getByText("同股优先相似样本")).toBeTruthy();
    expect(screen.getByText(/会优先展示当前股票历史上最接近的波段样本/)).toBeTruthy();
    expect(screen.getByText(/相似率综合了价格、K线形态、成交量、换手率、趋势背景和波动率/)).toBeTruthy();
    expect(screen.getByText(/样本股票 600157/)).toBeTruthy();
    expect(screen.getByText(/相似窗口：2025-08-01 至 2025-08-07/)).toBeTruthy();
    expect(screen.getByText(/所属波段：2025-08-01 至 2025-09-12/)).toBeTruthy();
    expect(screen.getByText(/相似度 83.4%/)).toBeTruthy();
    expect(screen.getByText(/价格相似 78.1%/)).toBeTruthy();
    expect(screen.getByText(/成交量相似 86.4%/)).toBeTruthy();
    expect(screen.getByText(/换手率相似 74.2%/)).toBeTruthy();
    expect(screen.getByText(/K线形态相似 90.1%/)).toBeTruthy();
    expect(screen.getByText(/趋势背景相似 68.8%/)).toBeTruthy();
    expect(screen.getByText(/波动率相似 74.4%/)).toBeTruthy();
    expect(screen.getByText(/样本区间涨跌幅 \+12.36%/)).toBeTruthy();
    expect(screen.getByText(/样本后续1日涨跌幅 \+1.50%/)).toBeTruthy();
    expect(screen.getByText(/样本后续3日涨跌幅 -2.20%/)).toBeTruthy();
    expect(screen.getByText(/样本后续5日涨跌幅 \+4.80%/)).toBeTruthy();
    expect(screen.getByText(/样本后续10日涨跌幅 \+12.60%/)).toBeTruthy();
  });

  it("opens a modal with current and historical charts", async () => {
    const loadSegmentChartWindow = vi.fn().mockImplementation(async (segmentId: number) => buildChartWindow(segmentId));

    render(
      <SimilarCaseList
        currentChartWindow={buildCurrentChartWindow()}
        loadSegmentChartWindow={loadSegmentChartWindow}
        items={[
          {
            segment_id: 12,
            stock_code: "600157",
            score: 0.8342,
            pct_change: 12.36,
            start_date: "2025-08-01",
            end_date: "2025-09-12",
            window_id: 301,
            window_start_date: "2025-08-01",
            window_end_date: "2025-08-07",
            segment_start_date: "2025-08-01",
            segment_end_date: "2025-09-12",
          },
          {
            segment_id: 18,
            stock_code: "600010",
            score: 0.8011,
            pct_change: -8.4,
            start_date: "2024-12-19",
            end_date: "2025-01-13",
            window_id: 302,
            window_start_date: "2024-12-19",
            window_end_date: "2024-12-27",
            segment_start_date: "2024-12-19",
            segment_end_date: "2025-01-13",
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "查看样本 12 K线对比" }));
    await waitFor(() => {
      expect(loadSegmentChartWindow).toHaveBeenCalledWith(12);
    });

    await waitFor(() => {
      expect(screen.getByRole("dialog", { name: "样本 12 K线对比" })).toBeTruthy();
    });
    expect(screen.getByText("当前相似窗口")).toBeTruthy();
    expect(screen.getByText("历史相似窗口")).toBeTruthy();
    expect(screen.getAllByTestId("kline-canvas")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "放大" })).toBeNull();
    expect(screen.queryByRole("button", { name: "缩小" })).toBeNull();
  });

  it("keeps each chart window intact instead of trimming historical context to match current", async () => {
    const currentChartWindow = {
      segment: {
        id: 0,
        stock_code: "600010",
        start_date: "2026-03-02",
        end_date: "2026-03-05",
      },
      highlight_range: {
        start_date: "2026-03-02",
        end_date: "2026-03-05",
      },
      prices: [
        { trade_date: "2026-02-27", open_price: 2.11, high_price: 2.14, low_price: 2.08, close_price: 2.12, volume: 120000 },
        { trade_date: "2026-03-02", open_price: 2.12, high_price: 2.16, low_price: 2.01, close_price: 2.03, volume: 180000 },
        { trade_date: "2026-03-03", open_price: 2.03, high_price: 2.05, low_price: 1.98, close_price: 2.0, volume: 190000 },
        { trade_date: "2026-03-04", open_price: 2.0, high_price: 2.02, low_price: 1.95, close_price: 1.98, volume: 170000 },
        { trade_date: "2026-03-05", open_price: 1.98, high_price: 2.01, low_price: 1.92, close_price: 1.94, volume: 160000 },
        { trade_date: "2026-03-06", open_price: 1.94, high_price: 1.98, low_price: 1.9, close_price: 1.92, volume: 150000 },
        { trade_date: "2026-03-09", open_price: 1.92, high_price: 1.94, low_price: 1.88, close_price: 1.9, volume: 140000 },
      ],
      auto_turning_points: [],
      final_turning_points: [
        { point_date: "2026-03-02", point_type: "peak", point_price: 2.03, source_type: "system" },
        { point_date: "2026-03-05", point_type: "trough", point_price: 1.94, source_type: "system" },
      ],
    };
    const historicalChartWindow = {
      segment: {
        id: 12,
        stock_code: "600157",
        start_date: "2025-08-01",
        end_date: "2025-08-06",
      },
      highlight_range: {
        start_date: "2025-08-01",
        end_date: "2025-08-06",
      },
      prices: [
        { trade_date: "2025-07-25", open_price: 5.4, high_price: 5.5, low_price: 5.3, close_price: 5.35, volume: 100000 },
        { trade_date: "2025-07-28", open_price: 5.35, high_price: 5.38, low_price: 5.3, close_price: 5.32, volume: 105000 },
        { trade_date: "2025-07-29", open_price: 5.32, high_price: 5.34, low_price: 5.25, close_price: 5.28, volume: 110000 },
        { trade_date: "2025-07-30", open_price: 5.28, high_price: 5.3, low_price: 5.22, close_price: 5.24, volume: 115000 },
        { trade_date: "2025-07-31", open_price: 5.24, high_price: 5.26, low_price: 5.19, close_price: 5.22, volume: 120000 },
        { trade_date: "2025-08-01", open_price: 5.22, high_price: 5.24, low_price: 5.1, close_price: 5.12, volume: 130000 },
        { trade_date: "2025-08-04", open_price: 5.12, high_price: 5.14, low_price: 5.02, close_price: 5.04, volume: 140000 },
        { trade_date: "2025-08-05", open_price: 5.04, high_price: 5.08, low_price: 4.96, close_price: 4.99, volume: 150000 },
        { trade_date: "2025-08-06", open_price: 4.99, high_price: 5.02, low_price: 4.9, close_price: 4.94, volume: 160000 },
        { trade_date: "2025-08-07", open_price: 4.94, high_price: 4.97, low_price: 4.88, close_price: 4.9, volume: 150000 },
        { trade_date: "2025-08-08", open_price: 4.9, high_price: 4.95, low_price: 4.85, close_price: 4.92, volume: 145000 },
      ],
      auto_turning_points: [],
      final_turning_points: [
        { point_date: "2025-08-01", point_type: "peak", point_price: 5.12, source_type: "system" },
        { point_date: "2025-08-06", point_type: "trough", point_price: 4.94, source_type: "system" },
      ],
    };
    const loadSegmentChartWindow = vi.fn().mockResolvedValue(historicalChartWindow);

    render(
      <SimilarCaseList
        currentChartWindow={currentChartWindow}
        loadSegmentChartWindow={loadSegmentChartWindow}
        items={[
          {
            segment_id: 12,
            stock_code: "600157",
            score: 0.8342,
            pct_change: -4.23,
            start_date: "2025-08-01",
            end_date: "2025-08-06",
            window_id: 401,
            window_start_date: "2025-08-01",
            window_end_date: "2025-08-06",
            segment_start_date: "2025-08-01",
            segment_end_date: "2025-08-06",
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "查看样本 12 K线对比" }));

    await waitFor(() => {
      expect(screen.getByRole("dialog", { name: "样本 12 K线对比" })).toBeTruthy();
    });

    const currentSection = screen.getByText("当前相似窗口").closest("section");
    const historicalSection = screen.getByText("历史相似窗口").closest("section");

    expect(currentSection).toBeTruthy();
    expect(historicalSection).toBeTruthy();
    expect(currentSection?.querySelectorAll('[data-testid="candlestick-body"]')).toHaveLength(7);
    expect(historicalSection?.querySelectorAll('[data-testid="candlestick-body"]')).toHaveLength(11);
  });
});
