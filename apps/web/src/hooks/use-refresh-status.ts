import { useEffect, useState } from "react";

import type { ApiClient, StockRefreshStatusData } from "../lib/api";

type RefreshStatusHookState = {
  data: StockRefreshStatusData | null;
  loading: boolean;
  error: string | null;
};

const ACTIVE_REFRESH_STATUSES = new Set<StockRefreshStatusData["status"]>(["queued", "running"]);

export function useRefreshStatus(
  stockCode: string,
  apiClient: Pick<ApiClient, "getStockRefreshStatus">,
): RefreshStatusHookState {
  const [data, setData] = useState<StockRefreshStatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStatus = apiClient.getStockRefreshStatus;
    if (!stockCode || loadStatus === undefined) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      setLoading(true);
      try {
        const next = await loadStatus(stockCode);
        if (cancelled) {
          return;
        }
        setData(next);
        setError(null);
        if (ACTIVE_REFRESH_STATUSES.has(next.status)) {
          timer = setTimeout(() => {
            void poll();
          }, 5000);
        }
      } catch (pollError) {
        if (!cancelled) {
          const message = pollError instanceof Error ? pollError.message : "Failed to load refresh status";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        clearTimeout(timer);
      }
    };
  }, [apiClient, stockCode]);

  return { data, loading, error };
}
