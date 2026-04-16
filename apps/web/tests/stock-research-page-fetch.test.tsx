// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import StockResearchPage from "../src/app/stocks/[stockCode]/page";
import type { ApiClient, StockResearchData, StockRefreshStatusData } from "../src/lib/api";

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
    ],
    auto_turning_points: [],
    final_turning_points: [],
    trade_markers: [],
    news_items: [
      {
        news_id: 1,
        title: "盈利预告改善",
        summary: "公告显示利润改善",
        source_name: "cninfo",
        source_type: "announcement",
        category: "announcement",
        sub_category: "earnings",
        sentiment: "positive",
        news_date: "2024-01-03",
        display_tags: ["当前波段内", "顶部前2日", "公告", "利多"],
        sentiment_score_adjusted: 0.82,
        event_types: ["earnings"],
        event_conflict_flag: false,
      },
    ],
    current_state: {
      label: "主升初期",
      summary: "主升初期，10日上行概率 0.58",
      probabilities: { up_10d: 0.58 },
      key_features: {},
      risk_flags: {},
      similar_cases: [],
      news_summary: {
        window_news_count: 3,
        announcement_count: 2,
        positive_news_ratio: 0.67,
        high_heat_count: 1,
        avg_adjusted_sentiment: 0.24,
        positive_event_count: 2,
        negative_event_count: 0,
        governance_event_count: 1,
      },
    },
  };
}

function buildRefreshStatus(status: StockRefreshStatusData["status"] = "success"): StockRefreshStatusData {
  return {
    stock_code: "000001",
    status,
    task_id: 101,
    updated_at: "2026-04-16T12:00:00Z",
    start_time: "2026-04-16T11:58:00Z",
    end_time: "2026-04-16T12:00:00Z",
    error_message: null,
  };
}

describe("stock research page fetch", () => {
  afterEach(() => cleanup());

  it("loads stock research data when initial data is absent", async () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn().mockResolvedValue(buildData()),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getStockRefreshStatus: vi.fn().mockResolvedValue(buildRefreshStatus()),
    };

    render(<StockResearchPage stockCode="000001" apiClient={apiClient} />);

    expect(screen.getByText("正在加载真实行情数据...")).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText("Ping An Bank (000001)")).toBeTruthy();
    });
    expect(screen.getByRole("link", { name: "Research" })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Main navigation" }).className).toContain("app-shell__top-nav");
    expect(screen.queryByLabelText("Primary")).toBeNull();
    expect(screen.getByText("Instrument Context")).toBeTruthy();
    expect(screen.getByText("Chart Workspace")).toBeTruthy();
    expect(screen.getByText("Event Flow")).toBeTruthy();
    expect(await screen.findByText(/最近刷新/)).toBeTruthy();
    expect(screen.getByTestId("research-workspace").className).toContain("terminal-grid--workspace-priority");
    expect(apiClient.getStockResearch).toHaveBeenCalledWith("000001");
  });

  it("searches by stock code and reloads the page data", async () => {
    const firstData = buildData();
    const secondData: StockResearchData = {
      ...buildData(),
      stock: {
        stock_code: "600157",
        stock_name: "永泰能源",
        market: "A",
        industry: "煤炭",
        concept_tags: ["能源"],
      },
    };
    const apiClient: ApiClient = {
      getStockResearch: vi.fn().mockImplementation(async (stockCode: string) => {
        if (stockCode === "000001") {
          return firstData;
        }
        if (stockCode === "600157") {
          return secondData;
        }
        throw new Error(`unexpected stock code: ${stockCode}`);
      }),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getStockRefreshStatus: vi.fn().mockResolvedValue(buildRefreshStatus()),
    };

    render(<StockResearchPage stockCode="000001" apiClient={apiClient} />);

    await waitFor(() => {
      expect(screen.getByText("Ping An Bank (000001)")).toBeTruthy();
    });

    fireEvent.change(screen.getByLabelText("股票代码搜索"), { target: { value: "600157" } });
    fireEvent.click(screen.getByRole("button", { name: "搜索" }));

    await waitFor(() => {
      expect(screen.getByText("永泰能源 (600157)")).toBeTruthy();
    });
    expect(apiClient.getStockResearch).toHaveBeenNthCalledWith(1, "000001");
    expect(apiClient.getStockResearch).toHaveBeenNthCalledWith(2, "600157");
  });

  it("shows announcement badge in news list", async () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn().mockResolvedValue(buildData()),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getStockRefreshStatus: vi.fn().mockResolvedValue(buildRefreshStatus()),
    };

    render(<StockResearchPage stockCode="000001" apiClient={apiClient} />);

    await waitFor(() => {
      expect(screen.getByText("盈利预告改善")).toBeTruthy();
    });
    expect(screen.getByText("公告")).toBeTruthy();
    expect(screen.getByText("当前波段内")).toBeTruthy();
    expect(screen.getByText("顶部前2日")).toBeTruthy();
    const bullishTag = screen.getByText("利多");
    expect(bullishTag).toBeTruthy();
    expect(bullishTag.getAttribute("style")).toContain("255, 159, 172");
    expect(screen.getByText(/cninfo/)).toBeTruthy();
  });

  it("renders news sentiment summary and event metadata", async () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn().mockResolvedValue(buildData()),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getStockRefreshStatus: vi.fn().mockResolvedValue(buildRefreshStatus()),
    };

    render(<StockResearchPage stockCode="000001" apiClient={apiClient} />);

    await waitFor(() => {
      expect(screen.getByText("盈利预告改善")).toBeTruthy();
    });

    expect(screen.getByText("窗口新闻 3")).toBeTruthy();
    expect(screen.getByText("公告 2")).toBeTruthy();
    expect(screen.getByText("修正情绪 0.24")).toBeTruthy();
    expect(screen.getByText("正向事件 2")).toBeTruthy();
    expect(screen.getByText("治理事件 1")).toBeTruthy();
    expect(screen.getByText("earnings")).toBeTruthy();
    expect(screen.getByText("修正后情绪 0.82")).toBeTruthy();
  });

  it("hides market and industry line when industry is missing", async () => {
    const apiClient: ApiClient = {
      getStockResearch: vi.fn().mockResolvedValue({
        ...buildData(),
        stock: {
          ...buildData().stock,
          industry: null,
        },
      }),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getStockRefreshStatus: vi.fn().mockResolvedValue(buildRefreshStatus()),
    };

    render(<StockResearchPage stockCode="000001" apiClient={apiClient} />);

    await waitFor(() => {
      expect(screen.getByText("Ping An Bank (000001)")).toBeTruthy();
    });

    expect(screen.queryByText("A / Unknown")).toBeNull();
  });
});
