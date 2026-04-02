"use client";

import { useState } from "react";

import { KlineChart } from "./kline-chart";
import type { SegmentChartWindowData, SimilarCase } from "../lib/api";

type SimilarCaseListProps = {
  items: SimilarCase[];
  currentChartWindow: SegmentChartWindowData | null;
  loadSegmentChartWindow: (segmentId: number) => Promise<SegmentChartWindowData>;
};

function formatPercent(score?: number) {
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

function findHighlightIndexes(chartWindow: SegmentChartWindowData) {
  const startIndex = chartWindow.prices.findIndex((row) => row.trade_date === chartWindow.highlight_range.start_date);
  const endIndex = chartWindow.prices.findIndex((row) => row.trade_date === chartWindow.highlight_range.end_date);
  if (startIndex === -1 || endIndex === -1) {
    return null;
  }
  return {
    startIndex: Math.min(startIndex, endIndex),
    endIndex: Math.max(startIndex, endIndex),
  };
}

function sliceChartWindow(chartWindow: SegmentChartWindowData, startIndex: number, endIndex: number): SegmentChartWindowData {
  const prices = chartWindow.prices.slice(startIndex, endIndex + 1);
  const windowStartDate = prices[0]?.trade_date ?? chartWindow.highlight_range.start_date;
  const windowEndDate = prices[prices.length - 1]?.trade_date ?? chartWindow.highlight_range.end_date;

  return {
    ...chartWindow,
    prices,
    auto_turning_points: chartWindow.auto_turning_points.filter(
      (point) => point.point_date >= windowStartDate && point.point_date <= windowEndDate
    ),
    final_turning_points: chartWindow.final_turning_points.filter(
      (point) => point.point_date >= windowStartDate && point.point_date <= windowEndDate
    ),
  };
}

function normalizeCompareWindows(currentChartWindow: SegmentChartWindowData, historicalChartWindow: SegmentChartWindowData) {
  const currentHighlight = findHighlightIndexes(currentChartWindow);
  const historicalHighlight = findHighlightIndexes(historicalChartWindow);
  if (currentHighlight === null || historicalHighlight === null) {
    return {
      current: currentChartWindow,
      historical: historicalChartWindow,
    };
  }

  const sharedLeadingCount = Math.min(currentHighlight.startIndex, historicalHighlight.startIndex);
  const currentTrailingCount = currentChartWindow.prices.length - currentHighlight.endIndex - 1;
  const historicalTrailingCount = historicalChartWindow.prices.length - historicalHighlight.endIndex - 1;
  const sharedTrailingCount = Math.min(currentTrailingCount, historicalTrailingCount);

  return {
    current: sliceChartWindow(
      currentChartWindow,
      currentHighlight.startIndex - sharedLeadingCount,
      currentHighlight.endIndex + sharedTrailingCount
    ),
    historical: sliceChartWindow(
      historicalChartWindow,
      historicalHighlight.startIndex - sharedLeadingCount,
      historicalHighlight.endIndex + sharedTrailingCount
    ),
  };
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
  const compareWindows =
    currentChartWindow !== null && activeChartWindow !== null
      ? normalizeCompareWindows(currentChartWindow, activeChartWindow)
      : null;
  const currentCompareWindow = compareWindows?.current ?? currentChartWindow;
  const historicalCompareWindow = compareWindows?.historical ?? activeChartWindow;

  if (items.length === 0) {
    return (
      <section>
        <h3>同股优先相似样本</h3>
        <p>会优先展示当前股票历史上最接近的波段样本；如果同股样本不足，再补充全市场样本。目前还没有可比样本。</p>
      </section>
    );
  }

  return (
    <section>
      <h3>同股优先相似样本</h3>
      <p>会优先展示当前股票历史上最接近的波段样本；如果同股样本不足，再补充全市场样本。相似度越高，说明走势和当前越接近。</p>
      <p>相似率综合了价格、成交量、换手率和最近 10 根 K 线组合形态，会同时比较统计摘要和最近一段量价序列。</p>
      <ul style={{ display: "grid", gap: 12, padding: 0, listStyle: "none" }}>
        {items.map((item) => (
          <li
            key={item.segment_id}
            style={{
              padding: 14,
              borderRadius: 14,
              border: "1px solid #e5dccb",
              background: "#fffaf1",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>
              <strong>样本股票 {item.stock_code}</strong>
              <button
                type="button"
                aria-label={`查看样本 ${item.segment_id} K线对比`}
                onClick={() => {
                  void handleOpenChart(item.segment_id);
                }}
              >
                查看K线对比
              </button>
            </div>
            <div>时间段 {item.start_date ?? "--"} 至 {item.end_date ?? "--"}</div>
            <div>相似度 {(item.score * 100).toFixed(1)}%</div>
            <div>价格相似 {formatPercent(item.price_score)}</div>
            <div>成交量相似 {formatPercent(item.volume_score)}</div>
            <div>换手率相似 {formatPercent(item.turnover_score)}</div>
            <div>K线形态相似 {formatPercent(item.pattern_score)}</div>
            <div>样本区间涨跌幅 {formatPctChange(item.pct_change)}</div>
            <div>样本后续1日涨跌幅 {formatForwardReturn(item.return_1d)}</div>
            <div>样本后续3日涨跌幅 {formatForwardReturn(item.return_3d)}</div>
            <div>样本后续5日涨跌幅 {formatForwardReturn(item.return_5d)}</div>
            <div>样本后续10日涨跌幅 {formatForwardReturn(item.return_10d)}</div>
            <div>样本波段 ID {item.segment_id}</div>
          </li>
        ))}
      </ul>
      {activeItem === null ? null : (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`样本 ${activeItem.segment_id} K线对比`}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(15, 23, 42, 0.58)",
            display: "grid",
            placeItems: "center",
            padding: 20,
          }}
          onClick={() => setActiveSegmentId(null)}
        >
          <div
            style={{
              width: "min(1200px, 100%)",
              maxHeight: "90vh",
              overflow: "auto",
              borderRadius: 20,
              border: "1px solid #e7dcc8",
              background: "#fffdf8",
              boxShadow: "0 28px 70px rgba(15, 23, 42, 0.24)",
              padding: 20,
              display: "grid",
              gap: 16,
            }}
            onClick={(event) => event.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
              <div>
                <strong>样本股票 {activeItem.stock_code}</strong>
                <div>时间段 {activeItem.start_date ?? "--"} 至 {activeItem.end_date ?? "--"}</div>
              </div>
              <button type="button" onClick={() => setActiveSegmentId(null)}>
                关闭
              </button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
              <section style={{ display: "grid", gap: 8 }}>
                <strong>当前走势</strong>
                {currentCompareWindow === null ? (
                  <p>当前对比K线暂不可用</p>
                ) : (
                  <KlineChart
                    title={null}
                    mode="readonly"
                    width={520}
                    height={420}
                    prices={currentCompareWindow.prices}
                    autoPoints={currentCompareWindow.auto_turning_points}
                    finalPoints={currentCompareWindow.final_turning_points}
                    highlightRange={currentCompareWindow.highlight_range}
                  />
                )}
              </section>
              <section style={{ display: "grid", gap: 8 }}>
                <strong>历史样本</strong>
                {activeChartLoading ? <p>正在加载样本局部K线...</p> : null}
                {activeChartError === null ? null : <p>{activeChartError}</p>}
                {historicalCompareWindow === null ? null : (
                  <KlineChart
                    title={null}
                    mode="readonly"
                    width={520}
                    height={420}
                    prices={historicalCompareWindow.prices}
                    autoPoints={historicalCompareWindow.auto_turning_points}
                    finalPoints={historicalCompareWindow.final_turning_points}
                    highlightRange={historicalCompareWindow.highlight_range}
                  />
                )}
              </section>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
