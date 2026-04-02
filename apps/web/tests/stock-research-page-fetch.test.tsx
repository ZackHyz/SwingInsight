// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    ],
    auto_turning_points: [],
    final_turning_points: [],
    trade_markers: [],
    news_items: [],
    current_state: {
      label: "主升初期",
      summary: "主升初期，10日上行概率 0.58",
      probabilities: { up_10d: 0.58 },
      key_features: {},
      risk_flags: {},
      similar_cases: [],
    },
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
    };

    render(<StockResearchPage stockCode="000001" apiClient={apiClient} />);

    expect(screen.getByText("正在加载真实行情数据...")).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText("Ping An Bank (000001)")).toBeTruthy();
    });
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
});
