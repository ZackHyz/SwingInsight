// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import WatchlistPage from "../src/app/watchlist/page";
import type { ApiClient, MarketWatchlistData } from "../src/lib/api";

function buildData(): MarketWatchlistData {
  return {
    scan_date: "2026-04-16",
    rows: [
      {
        rank_no: 1,
        stock_code: "000001",
        stock_name: "Ping An Bank",
        rank_score: 0.8123,
        pattern_score: 0.66,
        confidence: 0.72,
        sample_count: 4,
        event_density: 0.15,
      },
      {
        rank_no: 2,
        stock_code: "600157",
        stock_name: "Yongtai Energy",
        rank_score: 0.6311,
        pattern_score: 0.44,
        confidence: 0.58,
        sample_count: 1,
        event_density: 0.06,
      },
    ],
  };
}

describe("watchlist page", () => {
  afterEach(() => cleanup());

  it("renders leaderboard rows and links to research page", () => {
    render(<WatchlistPage initialData={buildData()} />);

    expect(screen.getByRole("link", { name: "观察池" })).toBeTruthy();
    expect(screen.getByText("分级观察池")).toBeTruthy();
    expect(screen.getByText("候选榜单")).toBeTruthy();
    expect(screen.getByRole("link", { name: "000001" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "600157" })).toBeTruthy();
    expect(screen.getByText("· Ping An Bank")).toBeTruthy();
    expect(screen.getByText("· Yongtai Energy")).toBeTruthy();
    expect(screen.getByRole("link", { name: "000001" }).getAttribute("href")).toBe("/stocks/000001");
  });

  it("loads watchlist data from api when initial data is absent", async () => {
    const getWatchlist = vi.fn<NonNullable<ApiClient["getWatchlist"]>>().mockResolvedValue(buildData());
    const client: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getWatchlist,
    };

    render(<WatchlistPage apiClient={client} />);

    expect(screen.getByText("候选池同步中...")).toBeTruthy();

    await waitFor(() => {
      expect(getWatchlist).toHaveBeenCalledTimes(1);
      expect(screen.getByRole("link", { name: "000001" })).toBeTruthy();
    });
    expect(screen.queryByText("候选池同步中...")).toBeNull();
  });
});
