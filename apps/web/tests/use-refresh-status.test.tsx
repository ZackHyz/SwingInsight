// @vitest-environment jsdom

import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useRefreshStatus } from "../src/hooks/use-refresh-status";
import { useWatchlistRefreshStatus } from "../src/hooks/use-watchlist-refresh-status";
import type { ApiClient, StockRefreshStatusData } from "../src/lib/api";

type ProbeProps = {
  stockCode: string;
  apiClient: Pick<ApiClient, "getStockRefreshStatus">;
};

function HookProbe({ stockCode, apiClient }: ProbeProps) {
  const state = useRefreshStatus(stockCode, apiClient);
  return (
    <div>
      <span data-testid="refresh-status">{state.data?.status ?? "none"}</span>
      <span data-testid="refresh-loading">{state.loading ? "loading" : "idle"}</span>
      <span data-testid="refresh-error">{state.error ?? "none"}</span>
    </div>
  );
}

function WatchlistHookProbe({ apiClient, requestVersion }: { apiClient: Pick<ApiClient, "getWatchlistRefreshStatus">; requestVersion: number }) {
  const state = useWatchlistRefreshStatus(requestVersion, apiClient);
  return (
    <div>
      <span data-testid="watchlist-refresh-status">{state.data?.status ?? "none"}</span>
      <span data-testid="watchlist-refresh-loading">{state.loading ? "loading" : "idle"}</span>
      <span data-testid="watchlist-refresh-error">{state.error ?? "none"}</span>
    </div>
  );
}

function buildStatus(status: StockRefreshStatusData["status"]): StockRefreshStatusData {
  return {
    stock_code: "600157",
    status,
    task_id: 1,
    updated_at: "2026-04-16T10:00:00Z",
    start_time: "2026-04-16T09:59:00Z",
    end_time: status === "running" ? null : "2026-04-16T10:00:00Z",
    error_message: null,
  };
}

describe("use refresh status", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("polls every 5s while refresh is queued or running", async () => {
    vi.useFakeTimers();
    const getStockRefreshStatus = vi
      .fn()
      .mockResolvedValueOnce(buildStatus("running"))
      .mockResolvedValueOnce(buildStatus("success"));

    render(<HookProbe stockCode="600157" apiClient={{ getStockRefreshStatus }} />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("refresh-status").textContent).toBe("running");
    expect(getStockRefreshStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(screen.getByTestId("refresh-status").textContent).toBe("success");
    expect(getStockRefreshStatus).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(getStockRefreshStatus).toHaveBeenCalledTimes(2);
  });

  it("keeps default state when api client has no refresh endpoint", async () => {
    render(<HookProbe stockCode="600157" apiClient={{ getStockRefreshStatus: undefined }} />);
    await waitFor(() => {
      expect(screen.getByTestId("refresh-status").textContent).toBe("none");
    });
    expect(screen.getByTestId("refresh-loading").textContent).toBe("idle");
    expect(screen.getByTestId("refresh-error").textContent).toBe("none");
  });
});

describe("use watchlist refresh status", () => {
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("polls every 3s while watchlist refresh is queued or running", async () => {
    vi.useFakeTimers();
    const getWatchlistRefreshStatus = vi
      .fn()
      .mockResolvedValueOnce({ task_id: 1, status: "running", updated_at: "2026-04-17T00:00:00Z" })
      .mockResolvedValueOnce({ task_id: 1, status: "success", updated_at: "2026-04-17T00:00:03Z" });

    render(<WatchlistHookProbe requestVersion={1} apiClient={{ getWatchlistRefreshStatus }} />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("watchlist-refresh-status").textContent).toBe("running");
    expect(getWatchlistRefreshStatus).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(screen.getByTestId("watchlist-refresh-status").textContent).toBe("success");
    expect(getWatchlistRefreshStatus).toHaveBeenCalledTimes(2);
  });
});
