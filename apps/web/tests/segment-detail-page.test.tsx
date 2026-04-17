// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import SegmentDetailPage from "../src/app/segments/[segmentId]/page";
import type { ApiClient, SegmentChartWindowData, SegmentDetailData } from "../src/lib/api";

function buildData(): SegmentDetailData {
  return {
    segment: {
      id: 1,
      stock_code: "000001",
      trend_direction: "up",
      start_date: "2024-01-04",
      end_date: "2024-01-08",
      start_price: 8.8,
      end_price: 10.6,
      pct_change: 20.4545,
      duration_days: 4,
      max_drawdown_pct: -2.2727,
      max_upside_pct: 21.5909,
      avg_daily_change_pct: 6.8182,
    },
    news_timeline: [
      {
        news_id: 11,
        title: "Bank support policy",
        summary: "Support before trough",
        source_name: "source-a",
        relation_type: "before_trough",
        distance_days: -2,
        news_date: "2024-01-02",
      },
      {
        news_id: 12,
        title: "Quarterly preview",
        summary: "Inside segment",
        source_name: "source-b",
        relation_type: "inside_segment",
        distance_days: 2,
        news_date: "2024-01-06",
      },
    ],
    labels: [
      {
        label_type: "pattern",
        label_name: "放量突破型",
        label_value: "matched",
      },
    ],
  };
}

function buildChartData(): SegmentChartWindowData {
  return {
    segment: {
      id: 1,
      stock_code: "000001",
      start_date: "2024-01-04",
      end_date: "2024-01-08",
    },
    highlight_range: {
      start_date: "2024-01-04",
      end_date: "2024-01-08",
    },
    prices: [
      { trade_date: "2023-12-21", open_price: 8.0, high_price: 8.2, low_price: 7.9, close_price: 8.1, volume: 100000 },
      { trade_date: "2023-12-22", open_price: 8.1, high_price: 8.2, low_price: 8.0, close_price: 8.15, volume: 110000 },
      { trade_date: "2024-01-04", open_price: 8.8, high_price: 9.0, low_price: 8.7, close_price: 8.95, volume: 180000 },
      { trade_date: "2024-01-05", open_price: 8.95, high_price: 9.8, low_price: 8.9, close_price: 9.7, volume: 220000 },
      { trade_date: "2024-01-08", open_price: 9.9, high_price: 10.7, low_price: 9.8, close_price: 10.6, volume: 260000 },
      { trade_date: "2024-01-09", open_price: 10.5, high_price: 10.6, low_price: 10.1, close_price: 10.2, volume: 210000 },
      { trade_date: "2024-01-10", open_price: 10.2, high_price: 10.4, low_price: 10.0, close_price: 10.1, volume: 190000 },
    ],
    auto_turning_points: [{ point_date: "2024-01-08", point_type: "peak", point_price: 10.7, source_type: "system" }],
    final_turning_points: [{ point_date: "2024-01-04", point_type: "trough", point_price: 8.7, source_type: "manual" }],
  };
}

describe("segment detail page", () => {
  afterEach(() => cleanup());

  it("loads detail data and renders pattern labels when initial data is absent", async () => {
    const data = buildData();
    const chartData = buildChartData();
    const getSegmentDetail = vi.fn(async () => data);
    const getSegmentChartWindow = vi.fn(async () => chartData);
    const apiClient = {
      getSegmentDetail,
      getSegmentChartWindow,
    } satisfies Partial<ApiClient>;

    render(<SegmentDetailPage segmentId="1" apiClient={apiClient as ApiClient} />);

    await waitFor(() => expect(getSegmentDetail).toHaveBeenCalledWith("1"));
    await waitFor(() => expect(getSegmentChartWindow).toHaveBeenCalledWith("1"));
    expect(await screen.findByText("放量突破型")).toBeTruthy();
    expect(screen.getByText("000001 波段详情")).toBeTruthy();
    expect(screen.getByText("K线形态视图")).toBeTruthy();
    expect(screen.getByText("当前形态 2024-01-04 至 2024-01-08，上下文窗口包含前后各 10 个交易日。")).toBeTruthy();
    expect(screen.getByTestId("segment-highlight")).toBeTruthy();
  });

  it("renders segment summary and news timeline", () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn().mockResolvedValue(buildChartData()),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
    };

    render(
      <SegmentDetailPage
        segmentId="1"
        initialData={buildData()}
        apiClient={apiClient}
      />
    );

    expect(screen.getByRole("link", { name: "形态库" })).toBeTruthy();
    expect(screen.getByText("波段拆解")).toBeTruthy();
    expect(screen.getByText("000001 波段详情")).toBeTruthy();
    expect(screen.getByText("20.45%")).toBeTruthy();
    expect(screen.getByText("Bank support policy")).toBeTruthy();
    expect(screen.getByText("before_trough")).toBeTruthy();
    expect(screen.getByText("放量突破型")).toBeTruthy();
  });
});
