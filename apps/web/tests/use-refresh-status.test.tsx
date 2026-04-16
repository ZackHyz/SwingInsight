// @vitest-environment jsdom

import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useRefreshStatus } from "../src/hooks/use-refresh-status";
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
