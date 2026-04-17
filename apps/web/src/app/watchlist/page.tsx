"use client";

import { useEffect, useRef, useState } from "react";

import { AppShell } from "../../components/app-shell";
import { StatusPill } from "../../components/status-pill";
import { TerminalPanel } from "../../components/terminal-panel";
import { useWatchlistRefreshStatus } from "../../hooks/use-watchlist-refresh-status";
import { apiClient, type ApiClient, type MarketWatchlistData } from "../../lib/api";
import { getMarketValueClass } from "../../lib/market-tone";

type WatchlistPageProps = {
  initialData?: MarketWatchlistData;
  apiClient?: ApiClient;
};

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export default function WatchlistPage({ initialData, apiClient: client }: WatchlistPageProps) {
  const api = client ?? apiClient;
  const [data, setData] = useState<MarketWatchlistData | null>(initialData ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [watchlistRequestVersion, setWatchlistRequestVersion] = useState(0);
  const [watchlistRefreshRequested, setWatchlistRefreshRequested] = useState(false);
  const appliedRefreshTaskIdRef = useRef<number | null>(null);
  const refreshStatus = useWatchlistRefreshStatus(watchlistRefreshRequested, api);

  useEffect(() => {
    if (initialData !== undefined) {
      setData(initialData);
      setLoadError(null);
      return;
    }
    if (api.getWatchlist === undefined) {
      setData(null);
      setLoadError("当前环境未提供 watchlist 数据接口。");
      return;
    }
    if (api.startWatchlistRefresh !== undefined && refreshStatus.data?.status !== "success" && appliedRefreshTaskIdRef.current === null) {
      return;
    }

    let cancelled = false;
    setData(null);
    setLoadError(null);
    const loadWatchlist = api.startWatchlistRefresh === undefined && api.refreshWatchlist !== undefined ? api.refreshWatchlist : api.getWatchlist;
    if (loadWatchlist === undefined) {
      setLoadError("当前环境未提供 watchlist 数据接口。");
      return;
    }

    loadWatchlist()
      .then((nextData) => {
        if (!cancelled) {
          setData(nextData);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load watchlist";
          setLoadError(message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [api, initialData, refreshStatus.data?.status, watchlistRequestVersion]);

  useEffect(() => {
    if (initialData !== undefined) {
      setWatchlistRefreshRequested(false);
      return;
    }
    const startWatchlistRefresh = api.startWatchlistRefresh;
    if (startWatchlistRefresh === undefined) {
      if (api.refreshWatchlist !== undefined) {
        setWatchlistRequestVersion((current) => current + 1);
      }
      return;
    }

    let cancelled = false;
    setWatchlistRefreshRequested(true);
    startWatchlistRefresh()
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to start watchlist refresh";
          setLoadError(message);
          setWatchlistRefreshRequested(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, initialData]);

  useEffect(() => {
    if (!watchlistRefreshRequested || api.getWatchlist === undefined) {
      return;
    }
    const status = refreshStatus.data?.status;
    const taskId = refreshStatus.data?.task_id ?? null;
    if (status === "success" && taskId !== null) {
      if (appliedRefreshTaskIdRef.current === taskId) {
        return;
      }
      appliedRefreshTaskIdRef.current = taskId;
      setWatchlistRequestVersion((current) => current + 1);
      return;
    }
    if (status === "failed") {
      const message = refreshStatus.data?.error_message ?? "观察池刷新失败";
      setLoadError(message);
    }
  }, [api, refreshStatus.data, watchlistRefreshRequested]);

  const rows = data?.rows ?? [];
  const topRow = rows[0] ?? null;
  const isLoading = (data === null && loadError === null) || refreshStatus.data?.status === "queued" || refreshStatus.data?.status === "running";
  const scanDate = data?.scan_date ?? null;

  return (
    <AppShell
      currentPath="/watchlist"
      title="分级观察池"
      subtitle="汇总夜间市场扫描结果，按形态得分、置信度、样本支撑和事件密度排序。"
      topBarContent={
        <>
          <StatusPill label={`扫描日 ${scanDate ?? "--"}`} />
          <StatusPill
            label={`刷新 ${refreshStatus.data?.status === "running" ? "进行中" : refreshStatus.data?.status === "queued" ? "排队中" : refreshStatus.data?.status === "success" ? "已完成" : refreshStatus.data?.status === "failed" ? "失败" : "待命"}`}
            tone={refreshStatus.data?.status === "success" ? "success" : refreshStatus.data?.status === "failed" ? "danger" : "warning"}
          />
          <StatusPill label={`候选数 ${rows.length}`} tone={rows.length > 0 ? "success" : "default"} />
        </>
      }
    >
      <TerminalPanel title="扫描摘要" eyebrow="夜间扫描">
        {isLoading ? (
          <p className="terminal-copy">正在刷新并重算观察池，请稍候...</p>
        ) : loadError !== null ? (
          <p className="terminal-copy">加载扫描结果失败: {loadError}</p>
        ) : topRow === null ? (
          <p className="terminal-copy">暂无扫描结果，请先运行夜间扫描任务。</p>
        ) : (
          <div className="terminal-inline-metrics">
            <div className="metric-card">
              <p className="metric-card__eyebrow">榜首标的</p>
              <p className="metric-card__value">{topRow.stock_code}</p>
            </div>
            <div className="metric-card">
              <p className="metric-card__eyebrow">形态得分</p>
              <p className={`metric-card__value ${getMarketValueClass(topRow.pattern_score - 0.5)}`}>{formatPercent(topRow.pattern_score)}</p>
            </div>
            <div className="metric-card">
              <p className="metric-card__eyebrow">置信度</p>
              <p className="metric-card__value">{formatPercent(topRow.confidence)}</p>
            </div>
          </div>
        )}
      </TerminalPanel>

      <TerminalPanel title="候选榜单" eyebrow="市场候选">
        {isLoading ? (
          <p className="terminal-copy">候选池同步中...</p>
        ) : loadError !== null ? (
          <p className="terminal-copy">当前无法加载候选池: {loadError}</p>
        ) : rows.length === 0 ? (
          <p className="terminal-copy">当前没有可展示的候选池。</p>
        ) : (
          <table className="terminal-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>股票</th>
                <th>形态</th>
                <th>置信度</th>
                <th>样本数</th>
                <th>事件密度</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.stock_code}>
                  <td>{row.rank_no}</td>
                  <td>
                    <a className="terminal-link" href={`/stocks/${row.stock_code}`}>
                      {row.stock_code}
                    </a>
                    {row.stock_name ? ` · ${row.stock_name}` : ""}
                  </td>
                  <td className={getMarketValueClass(row.pattern_score - 0.5)}>{formatPercent(row.pattern_score)}</td>
                  <td>{formatPercent(row.confidence)}</td>
                  <td>{row.sample_count}</td>
                  <td>{row.event_density.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </TerminalPanel>
    </AppShell>
  );
}
