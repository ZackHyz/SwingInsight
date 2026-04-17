import { useEffect, useState } from "react";

import type { ApiClient, WatchlistRefreshTaskData } from "../lib/api";

type WatchlistRefreshState = {
  data: WatchlistRefreshTaskData | null;
  loading: boolean;
  error: string | null;
};

const ACTIVE_WATCHLIST_REFRESH_STATUSES = new Set<WatchlistRefreshTaskData["status"]>(["queued", "running"]);

export function useWatchlistRefreshStatus(
  requestVersion: number,
  apiClient: Pick<ApiClient, "getWatchlistRefreshStatus">,
): WatchlistRefreshState {
  const [data, setData] = useState<WatchlistRefreshTaskData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStatus = apiClient.getWatchlistRefreshStatus;
    if (loadStatus === undefined) {
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
        const next = await loadStatus();
        if (cancelled) {
          return;
        }
        setData(next);
        setError(null);
        if (ACTIVE_WATCHLIST_REFRESH_STATUSES.has(next.status)) {
          timer = setTimeout(() => {
            void poll();
          }, 3000);
        }
      } catch (pollError) {
        if (!cancelled) {
          const message = pollError instanceof Error ? pollError.message : "Failed to load watchlist refresh status";
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
  }, [apiClient, requestVersion]);

  return { data, loading, error };
}
