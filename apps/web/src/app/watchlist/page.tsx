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

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", { hour12: false });
}

export default function WatchlistPage({ initialData, apiClient: client }: WatchlistPageProps) {
  const api = client ?? apiClient;
  const [data, setData] = useState<MarketWatchlistData | null>(initialData ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [watchlistRequestVersion, setWatchlistRequestVersion] = useState(0);
  const [watchlistRefreshStatusVersion, setWatchlistRefreshStatusVersion] = useState(0);
  const appliedRefreshTaskIdRef = useRef<number | null>(null);
  const refreshStatus = useWatchlistRefreshStatus(watchlistRefreshStatusVersion, api);

  useEffect(() => {
    if (initialData !== undefined) {
      setData(initialData);
      setLoadError(null);
      return;
    }
    if (api.getWatchlist === undefined) {
      setLoadError("当前环境未提供 watchlist 数据接口。");
      return;
    }

    let cancelled = false;
    setLoadError(null);
    const loadWatchlist = api.getWatchlist;
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
  }, [api, initialData, watchlistRequestVersion]);

  useEffect(() => {
    if (api.getWatchlistRefreshStatus !== undefined) {
      setWatchlistRefreshStatusVersion((current) => current + 1);
    }
  }, [api]);

  useEffect(() => {
    if (initialData !== undefined || !isRefreshing) {
      return;
    }
    const status = refreshStatus.data?.status;
    const taskId = refreshStatus.data?.task_id ?? null;
    if (status === "success" && taskId !== null) {
      if (appliedRefreshTaskIdRef.current === taskId) {
        setIsRefreshing(false);
        return;
      }
      appliedRefreshTaskIdRef.current = taskId;
      setIsRefreshing(false);
      setWatchlistRequestVersion((current) => current + 1);
      return;
    }
    if (status === "failed") {
      const message = refreshStatus.data?.error_message ?? "观察池刷新失败";
      setLoadError(message);
      setIsRefreshing(false);
    }
  }, [initialData, isRefreshing, refreshStatus.data]);

  async function handleRefresh() {
    const startWatchlistRefresh = api.startWatchlistRefresh;
    if (startWatchlistRefresh === undefined) {
      setLoadError("当前环境未提供观察池刷新接口。");
      return;
    }
    setLoadError(null);
    setIsRefreshing(true);
    try {
      const task = await startWatchlistRefresh();
      appliedRefreshTaskIdRef.current = null;
      if (task.status === "success") {
        if (task.task_id !== null) {
          appliedRefreshTaskIdRef.current = task.task_id;
        }
        setIsRefreshing(false);
        setWatchlistRequestVersion((current) => current + 1);
        setWatchlistRefreshStatusVersion((current) => current + 1);
        return;
      }
      setWatchlistRefreshStatusVersion((current) => current + 1);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to start watchlist refresh";
      setLoadError(message);
      setIsRefreshing(false);
    }
  }

  const rows = data?.rows ?? [];
  const topRow = rows[0] ?? null;
  const isInitialLoading = data === null && loadError === null;
  const activeRefreshStatus = refreshStatus.data?.status;
  const refreshInProgress = isRefreshing || activeRefreshStatus === "queued" || activeRefreshStatus === "running";
  const scanDate = data?.scan_date ?? null;
  const refreshCompletedAt = refreshStatus.data?.end_time ?? null;
  const refreshStatusLabel =
    activeRefreshStatus === "running"
      ? "进行中"
      : activeRefreshStatus === "queued"
        ? "排队中"
        : activeRefreshStatus === "success"
          ? "已完成"
          : activeRefreshStatus === "failed"
            ? "失败"
            : "待命";

  return (
    <AppShell
      currentPath="/watchlist"
      title="分级观察池"
      subtitle="汇总夜间市场扫描结果，按形态得分、置信度、样本支撑和事件密度排序。"
      topBarContent={
        <>
          <StatusPill label={`扫描日 ${scanDate ?? "--"}`} />
          <StatusPill label={`本次刷新完成 ${formatDateTime(refreshCompletedAt)}`} tone={refreshCompletedAt ? "success" : "default"} />
          <StatusPill
            label={`刷新 ${refreshStatusLabel}`}
            tone={activeRefreshStatus === "success" ? "success" : activeRefreshStatus === "failed" ? "danger" : "warning"}
          />
          <StatusPill label={`候选数 ${rows.length}`} tone={rows.length > 0 ? "success" : "default"} />
          <button className="terminal-button terminal-button--primary" type="button" onClick={handleRefresh} disabled={refreshInProgress}>
            {refreshInProgress ? "刷新中..." : "刷新观察池"}
          </button>
        </>
      }
    >
      <TerminalPanel title="扫描摘要" eyebrow="夜间扫描">
        {isInitialLoading ? (
          <p className="terminal-copy">正在加载最近一次观察池结果...</p>
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
            <div className="metric-card">
              <p className="metric-card__eyebrow">榜首刷新时间</p>
              <p className="metric-card__value">{formatDateTime(topRow.latest_refresh_at)}</p>
            </div>
          </div>
        )}
        {refreshInProgress ? <p className="terminal-copy">观察池正在后台刷新，当前先展示上一次结果。</p> : null}
      </TerminalPanel>

      <TerminalPanel title="候选榜单" eyebrow="市场候选">
        {isInitialLoading ? (
          <p className="terminal-copy">候选池加载中...</p>
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
                <th>最新刷新时间</th>
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
                  <td>{formatDateTime(row.latest_refresh_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </TerminalPanel>
    </AppShell>
  );
}
