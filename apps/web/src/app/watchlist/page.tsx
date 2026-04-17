"use client";

import { useEffect, useState } from "react";

import { AppShell } from "../../components/app-shell";
import { StatusPill } from "../../components/status-pill";
import { TerminalPanel } from "../../components/terminal-panel";
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

    let cancelled = false;
    setData(null);
    setLoadError(null);
    api
      .getWatchlist()
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
  }, [api, initialData]);

  const rows = data?.rows ?? [];
  const topRow = rows[0] ?? null;
  const isLoading = data === null && loadError === null;
  const scanDate = data?.scan_date ?? null;

  return (
    <AppShell
      currentPath="/watchlist"
      title="Ranked Watchlist"
      subtitle="Nightly market scan output ranked by pattern score, confidence, sample support, and event density."
      topBarContent={
        <>
          <StatusPill label={`Scan ${scanDate ?? "--"}`} />
          <StatusPill label={`Rows ${rows.length}`} tone={rows.length > 0 ? "success" : "default"} />
        </>
      }
    >
      <TerminalPanel title="Scan Summary" eyebrow="Nightly Scan">
        {isLoading ? (
          <p className="terminal-copy">正在加载夜间扫描结果...</p>
        ) : loadError !== null ? (
          <p className="terminal-copy">加载扫描结果失败: {loadError}</p>
        ) : topRow === null ? (
          <p className="terminal-copy">暂无扫描结果，请先运行夜间扫描任务。</p>
        ) : (
          <div className="terminal-inline-metrics">
            <div className="metric-card">
              <p className="metric-card__eyebrow">Top Candidate</p>
              <p className="metric-card__value">{topRow.stock_code}</p>
            </div>
            <div className="metric-card">
              <p className="metric-card__eyebrow">Pattern Score</p>
              <p className={`metric-card__value ${getMarketValueClass(topRow.pattern_score - 0.5)}`}>{formatPercent(topRow.pattern_score)}</p>
            </div>
            <div className="metric-card">
              <p className="metric-card__eyebrow">Confidence</p>
              <p className="metric-card__value">{formatPercent(topRow.confidence)}</p>
            </div>
          </div>
        )}
      </TerminalPanel>

      <TerminalPanel title="Leaderboard" eyebrow="Market Candidates">
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
                <th>Rank</th>
                <th>Stock</th>
                <th>Pattern</th>
                <th>Confidence</th>
                <th>Sample</th>
                <th>Event Density</th>
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
