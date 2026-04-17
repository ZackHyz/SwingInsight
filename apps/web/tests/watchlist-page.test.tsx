// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
        latest_refresh_at: "2026-04-16T09:30:00Z",
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
        latest_refresh_at: "2026-04-16T09:20:00Z",
      },
    ],
  };
}

describe("watchlist page", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("renders leaderboard rows and links to research page", () => {
    render(<WatchlistPage initialData={buildData()} />);

    expect(screen.getByRole("link", { name: "观察池" })).toBeTruthy();
    expect(screen.getByText("分级观察池")).toBeTruthy();
    expect(screen.getByText("候选榜单")).toBeTruthy();
    expect(screen.getByRole("link", { name: "000001" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "600157" })).toBeTruthy();
    expect(screen.getByText("· Ping An Bank")).toBeTruthy();
    expect(screen.getByText("· Yongtai Energy")).toBeTruthy();
    expect(screen.getByText(/本次刷新完成/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "000001" }).getAttribute("href")).toBe("/stocks/000001");
  });

  it("loads previous watchlist data by default and refreshes only after button click", async () => {
    const getWatchlist = vi.fn<NonNullable<ApiClient["getWatchlist"]>>().mockResolvedValue(buildData());
    const startWatchlistRefresh = vi.fn<NonNullable<ApiClient["startWatchlistRefresh"]>>().mockResolvedValue({
      task_id: 1,
      status: "queued",
      created_at: "2026-04-17T00:00:00Z",
      updated_at: "2026-04-17T00:00:00Z",
      scan_date: null,
      row_count: null,
    });
    const getWatchlistRefreshStatus = vi
      .fn<NonNullable<ApiClient["getWatchlistRefreshStatus"]>>()
      .mockResolvedValueOnce({
        task_id: 9,
        status: "success",
        created_at: "2026-04-16T00:00:00Z",
        updated_at: "2026-04-16T00:00:01Z",
        end_time: "2026-04-16T00:00:01Z",
        scan_date: "2026-04-16",
        row_count: 2,
      })
      .mockResolvedValueOnce({
        task_id: 1,
        status: "success",
        created_at: "2026-04-17T00:00:00Z",
        updated_at: "2026-04-17T00:00:02Z",
        end_time: "2026-04-17T00:00:02Z",
        scan_date: "2026-04-17",
        row_count: 2,
      });
    const client: ApiClient = {
      getStockResearch: vi.fn(),
      commitTurningPoints: vi.fn(),
      getSegmentChartWindow: vi.fn(),
      getSegmentDetail: vi.fn(),
      getSegmentLibrary: vi.fn(),
      getPrediction: vi.fn(),
      getWatchlist,
      startWatchlistRefresh,
      getWatchlistRefreshStatus,
    };

    render(<WatchlistPage apiClient={client} />);

    await waitFor(() => {
      expect(getWatchlistRefreshStatus).toHaveBeenCalled();
      expect(getWatchlist).toHaveBeenCalledTimes(1);
      expect(screen.getByRole("link", { name: "000001" })).toBeTruthy();
    });
    expect(startWatchlistRefresh).toHaveBeenCalledTimes(0);

    fireEvent.click(screen.getByRole("button", { name: "刷新观察池" }));

    await waitFor(() => {
      expect(startWatchlistRefresh).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(getWatchlist).toHaveBeenCalledTimes(2);
    });
  });
});
