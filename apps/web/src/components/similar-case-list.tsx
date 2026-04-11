"use client";

import { useState } from "react";
import { createPortal } from "react-dom";

import { KlineChart } from "./kline-chart";
import { StatusPill } from "./status-pill";
import type { SegmentChartWindowData, SimilarCase } from "../lib/api";
import { getMarketValueClass, getSignedTone } from "../lib/market-tone";

type SimilarCaseListProps = {
  items: SimilarCase[];
  currentChartWindow: SegmentChartWindowData | null;
  loadSegmentChartWindow: (segmentId: number) => Promise<SegmentChartWindowData>;
};

function formatPercent(score?: number | null) {
  if (score === undefined || score === null) {
    return "--";
  }
  return `${(score * 100).toFixed(1)}%`;
}

function formatPctChange(pctChange?: number | null) {
  if (pctChange === undefined || pctChange === null) {
    return "--";
  }
  return `${pctChange >= 0 ? "+" : ""}${pctChange.toFixed(2)}%`;
}

function formatForwardReturn(value?: number | null) {
  if (value === undefined || value === null) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

export function SimilarCaseList({ items, currentChartWindow, loadSegmentChartWindow }: SimilarCaseListProps) {
  const [activeSegmentId, setActiveSegmentId] = useState<number | null>(null);
  const [chartWindows, setChartWindows] = useState<Record<number, SegmentChartWindowData>>({});
  const [loadingSegmentIds, setLoadingSegmentIds] = useState<Record<number, boolean>>({});
  const [chartErrors, setChartErrors] = useState<Record<number, string>>({});

  async function handleOpenChart(segmentId: number) {
    setActiveSegmentId(segmentId);
    if (chartWindows[segmentId] !== undefined || loadingSegmentIds[segmentId]) {
      return;
    }

    setLoadingSegmentIds((current) => ({ ...current, [segmentId]: true }));
    setChartErrors((current) => {
      const next = { ...current };
      delete next[segmentId];
      return next;
    });
    try {
      const payload = await loadSegmentChartWindow(segmentId);
      setChartWindows((current) => ({ ...current, [segmentId]: payload }));
    } catch {
      setChartErrors((current) => ({ ...current, [segmentId]: "样本局部K线加载失败" }));
    } finally {
      setLoadingSegmentIds((current) => ({ ...current, [segmentId]: false }));
    }
  }

  const activeItem = activeSegmentId === null ? null : items.find((item) => item.segment_id === activeSegmentId) ?? null;
  const activeChartWindow = activeSegmentId === null ? null : chartWindows[activeSegmentId] ?? null;
  const activeChartError = activeSegmentId === null ? null : chartErrors[activeSegmentId] ?? null;
  const activeChartLoading = activeSegmentId === null ? false : loadingSegmentIds[activeSegmentId] === true;
  if (items.length === 0) {
    return (
      <section className="terminal-stack">
        <h3>同股优先相似样本</h3>
        <p className="terminal-copy">会优先展示当前股票历史上最接近的波段样本；如果同股样本不足，再补充全市场样本。目前还没有可比样本。</p>
      </section>
    );
  }

  return (
    <section className="terminal-stack">
      <h3>同股优先相似样本</h3>
      <p className="terminal-copy">会优先展示当前股票历史上最接近的波段样本；如果同股样本不足，再补充全市场样本。相似度越高，说明走势和当前越接近。</p>
      <p className="terminal-copy">相似率综合了价格、K线形态、成交量、换手率、趋势背景和波动率，会同时比较固定 7 个交易日窗口的路径和结构。</p>
      <ul className="terminal-list">
        {items.map((item) => (
          <li
            key={`${item.segment_id}-${item.window_id ?? item.window_start_date ?? item.start_date ?? "case"}`}
            className="terminal-panel similar-case-card"
          >
            <div className="terminal-panel__body">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>
              <strong>样本股票 {item.stock_code}</strong>
              <button
                className="terminal-button"
                type="button"
                aria-label={`查看样本 ${item.segment_id} K线对比`}
                onClick={() => {
                  void handleOpenChart(item.segment_id);
                }}
              >
                查看K线对比
              </button>
              </div>
              <div>相似窗口：{item.window_start_date ?? item.start_date ?? "--"} 至 {item.window_end_date ?? item.end_date ?? "--"}</div>
              <div>所属波段：{item.segment_start_date ?? item.start_date ?? "--"} 至 {item.segment_end_date ?? item.end_date ?? "--"}</div>
              <div>相似度 {(item.score * 100).toFixed(1)}%</div>
              <div>价格相似 {formatPercent(item.price_score)}</div>
              <div>成交量相似 {formatPercent(item.volume_score)}</div>
              <div>换手率相似 {formatPercent(item.turnover_score)}</div>
              <div>K线形态相似 {formatPercent(item.candle_score ?? item.pattern_score)}</div>
              <div>趋势背景相似 {formatPercent(item.trend_score)}</div>
              <div>波动率相似 {formatPercent(item.vola_score)}</div>
              <div>样本区间涨跌幅 <span className={getMarketValueClass(item.pct_change)}>{formatPctChange(item.pct_change)}</span></div>
              <div>样本后续1日涨跌幅 <span className={getMarketValueClass(item.return_1d)}>{formatForwardReturn(item.return_1d)}</span></div>
              <div>样本后续3日涨跌幅 <span className={getMarketValueClass(item.return_3d)}>{formatForwardReturn(item.return_3d)}</span></div>
              <div>样本后续5日涨跌幅 <span className={getMarketValueClass(item.return_5d)}>{formatForwardReturn(item.return_5d)}</span></div>
              <div>样本后续10日涨跌幅 <span className={getMarketValueClass(item.return_10d)}>{formatForwardReturn(item.return_10d)}</span></div>
              <div>样本波段 ID {item.segment_id}</div>
            </div>
          </li>
        ))}
      </ul>
      {activeItem === null || typeof document === "undefined"
        ? null
        : createPortal(
            <div
              role="dialog"
              aria-modal="true"
              aria-label={`样本 ${activeItem.segment_id} K线对比`}
              className="terminal-dialog terminal-dialog--fullscreen"
              onClick={() => setActiveSegmentId(null)}
            >
              <div
                className="terminal-dialog__panel terminal-dialog__panel--fullscreen"
                data-testid="similar-case-dialog-panel"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="terminal-dialog__header">
                  <div>
                    <strong>样本股票 {activeItem.stock_code}</strong>
                    <div>相似窗口：{activeItem.window_start_date ?? activeItem.start_date ?? "--"} 至 {activeItem.window_end_date ?? activeItem.end_date ?? "--"}</div>
                    <div>所属波段：{activeItem.segment_start_date ?? activeItem.start_date ?? "--"} 至 {activeItem.segment_end_date ?? activeItem.end_date ?? "--"}</div>
                    <div className="terminal-dialog__meta">
                      <StatusPill label={`相似度 ${(activeItem.score * 100).toFixed(1)}%`} />
                      <StatusPill label={`区间涨跌幅 ${formatPctChange(activeItem.pct_change)}`} tone={getSignedTone(activeItem.pct_change)} />
                      <StatusPill label={`后续5日 ${formatForwardReturn(activeItem.return_5d)}`} tone={getSignedTone(activeItem.return_5d)} />
                      <StatusPill label={`后续10日 ${formatForwardReturn(activeItem.return_10d)}`} tone={getSignedTone(activeItem.return_10d)} />
                    </div>
                  </div>
                  <button className="terminal-button" type="button" onClick={() => setActiveSegmentId(null)}>
                    关闭
                  </button>
                </div>
                <div className="terminal-chart-grid terminal-chart-grid--comparison" data-testid="similar-case-dialog-content">
                  <section className="terminal-stack terminal-chart-section">
                    <strong>当前相似窗口</strong>
                    {currentChartWindow === null ? (
                      <p>当前对比K线暂不可用</p>
                    ) : (
                      <div className="terminal-chart-frame">
                        <KlineChart
                          title={null}
                          mode="readonly"
                          width={860}
                          height={520}
                          prices={currentChartWindow.prices}
                          autoPoints={currentChartWindow.auto_turning_points}
                          finalPoints={currentChartWindow.final_turning_points}
                          highlightRange={currentChartWindow.highlight_range}
                        />
                      </div>
                    )}
                  </section>
                  <section className="terminal-stack terminal-chart-section">
                    <strong>历史相似窗口</strong>
                    {activeChartLoading ? <p className="terminal-copy">正在加载样本局部K线...</p> : null}
                    {activeChartError === null ? null : <p className="terminal-copy">{activeChartError}</p>}
                    {activeChartWindow === null ? null : (
                      <div className="terminal-chart-frame">
                        <KlineChart
                          title={null}
                          mode="readonly"
                          width={860}
                          height={520}
                          prices={activeChartWindow.prices}
                          autoPoints={activeChartWindow.auto_turning_points}
                          finalPoints={activeChartWindow.final_turning_points}
                          highlightRange={activeChartWindow.highlight_range}
                        />
                      </div>
                    )}
                  </section>
                </div>
              </div>
            </div>,
            document.body
          )}
    </section>
  );
}
