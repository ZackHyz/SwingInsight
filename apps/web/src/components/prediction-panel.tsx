import { SimilarCaseList } from "./similar-case-list";
import { PatternScoreCard } from "./pattern-score-card";
import type { ApiClient, QueryWindow, SegmentChartWindowData, StockResearchData } from "../lib/api";
import { getMarketValueClass } from "../lib/market-tone";
import { usePatternInsight } from "../hooks/use-pattern-insight";

type PredictionPanelProps = {
  apiClient: Pick<ApiClient, "getSegmentChartWindow" | "getPatternScore" | "getPatternSimilarCases" | "getPatternGroupStat">;
  stockCode: string;
  prices: StockResearchData["prices"];
  autoPoints: StockResearchData["auto_turning_points"];
  finalPoints: StockResearchData["final_turning_points"];
  currentState: StockResearchData["current_state"];
};

const CONTEXT_TRADING_DAYS = 10;

const PROBABILITY_LABELS: Record<string, string> = {
  up_1d: "次日上涨",
  flat_1d: "次日震荡",
  down_1d: "次日下跌",
  up_5d: "5日上涨",
  flat_5d: "5日震荡",
  down_5d: "5日下跌",
  up_10d: "10日上涨",
  flat_10d: "10日震荡",
  down_10d: "10日下跌",
  up_20d: "20日上涨",
  flat_20d: "20日震荡",
  down_20d: "20日下跌",
};

const FEATURE_LABELS: Record<string, string> = {
  volume_ratio_5d: "量比(5日)",
  positive_news_ratio: "正向新闻占比",
  pct_change: "区间涨跌幅",
  max_drawdown_pct: "最大回撤",
};

const RISK_LABELS: Record<string, string> = {
  pullback_risk: "回撤风险",
  news_support: "消息支撑",
};

const RISK_VALUE_LABELS: Record<string, string> = {
  low: "低",
  high: "高",
  strong: "强",
  weak: "弱",
};

function buildCurrentChartWindow({
  stockCode,
  prices,
  autoPoints,
  finalPoints,
  queryWindow,
}: Pick<PredictionPanelProps, "stockCode" | "prices" | "autoPoints" | "finalPoints"> & {
  queryWindow?: QueryWindow | null;
}): SegmentChartWindowData | null {
  if (prices.length === 0) {
    return null;
  }

  let windowStartIndex = Math.max(prices.length - (CONTEXT_TRADING_DAYS * 2 + 3), 0);
  let windowEndIndex = prices.length;
  let highlightStartDate = prices[Math.max(prices.length - 2, 0)].trade_date;
  let highlightEndDate = prices[prices.length - 1].trade_date;

  if (queryWindow !== undefined && queryWindow !== null) {
    const startIndex = prices.findIndex((row) => row.trade_date === queryWindow.start_date);
    const endIndex = prices.findIndex((row) => row.trade_date === queryWindow.end_date);
    if (startIndex !== -1 && endIndex !== -1) {
      const leftIndex = Math.min(startIndex, endIndex);
      const rightIndex = Math.max(startIndex, endIndex);
      windowStartIndex = Math.max(leftIndex - CONTEXT_TRADING_DAYS, 0);
      windowEndIndex = Math.min(rightIndex + CONTEXT_TRADING_DAYS + 1, prices.length);
      highlightStartDate = prices[leftIndex].trade_date;
      highlightEndDate = prices[rightIndex].trade_date;
    }
  } else if (finalPoints.length >= 2) {
    const startPoint = finalPoints[finalPoints.length - 2];
    const endPoint = finalPoints[finalPoints.length - 1];
    const startIndex = prices.findIndex((row) => row.trade_date === startPoint.point_date);
    const endIndex = prices.findIndex((row) => row.trade_date === endPoint.point_date);
    if (startIndex !== -1 && endIndex !== -1) {
      const leftIndex = Math.min(startIndex, endIndex);
      const rightIndex = Math.max(startIndex, endIndex);
      windowStartIndex = Math.max(leftIndex - CONTEXT_TRADING_DAYS, 0);
      windowEndIndex = Math.min(rightIndex + CONTEXT_TRADING_DAYS + 1, prices.length);
      highlightStartDate = prices[leftIndex].trade_date;
      highlightEndDate = prices[rightIndex].trade_date;
    }
  }

  const windowPrices = prices.slice(windowStartIndex, windowEndIndex);
  const windowStartDate = windowPrices[0]?.trade_date ?? highlightStartDate;
  const windowEndDate = windowPrices[windowPrices.length - 1]?.trade_date ?? highlightEndDate;

  return {
    segment: {
      id: 0,
      stock_code: stockCode,
      start_date: highlightStartDate,
      end_date: highlightEndDate,
    },
    highlight_range: {
      start_date: highlightStartDate,
      end_date: highlightEndDate,
    },
    prices: windowPrices,
    auto_turning_points: autoPoints.filter((point) => point.point_date >= windowStartDate && point.point_date <= windowEndDate),
    final_turning_points: finalPoints.filter((point) => point.point_date >= windowStartDate && point.point_date <= windowEndDate),
  };
}

function formatSignedPercent(value?: number) {
  if (value === undefined || value === null) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function formatPercent(value?: number) {
  if (value === undefined || value === null) {
    return "--";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function getProbabilityValueClass(key: string): string {
  if (key.startsWith("up_")) {
    return "market-value market-value--positive";
  }
  if (key.startsWith("down_")) {
    return "market-value market-value--negative";
  }
  return "market-value market-value--neutral";
}

export function PredictionPanel({ apiClient, stockCode, prices, autoPoints, finalPoints, currentState }: PredictionPanelProps) {
  const patternInsight = usePatternInsight(stockCode, apiClient);
  const probabilities = currentState.probabilities ?? {};
  const keyFeatures = currentState.key_features ?? {};
  const riskFlags = currentState.risk_flags ?? {};
  const similarCases = currentState.similar_cases ?? [];
  const groupStat = currentState.group_stat;
  const currentChartWindow = buildCurrentChartWindow({
    stockCode,
    prices,
    autoPoints,
    finalPoints,
    queryWindow: currentState.query_window,
  });

  return (
    <aside className="terminal-panel">
      <header className="terminal-panel__header">
        <div>
          <p className="terminal-panel__eyebrow">Intelligence Rail</p>
          <h2 className="terminal-panel__title">预测面板</h2>
        </div>
      </header>
      <div className="terminal-panel__body">
        <p className="terminal-copy">当前状态: {currentState.label}</p>
        <p className="terminal-copy">{currentState.summary}</p>
        <section className="terminal-stack">
          <h3>方向概率</h3>
          <ul className="terminal-list">
          {Object.entries(probabilities).map(([key, value]) => (
            <li key={key}>
              {PROBABILITY_LABELS[key] ?? key} <span className={getProbabilityValueClass(key)}>{(value * 100).toFixed(1)}%</span>
            </li>
          ))}
          </ul>
        </section>
        <section className="terminal-stack">
          <h3>关键触发特征</h3>
          <ul className="terminal-list">
          {Object.entries(keyFeatures).map(([key, value]) => (
            <li key={key}>
              {FEATURE_LABELS[key] ?? key}{" "}
              <span className={key === "pct_change" || key === "max_drawdown_pct" ? getMarketValueClass(value) : "market-value market-value--neutral"}>
                {value}
              </span>
            </li>
          ))}
          </ul>
        </section>
        <section className="terminal-stack">
          <h3>风险提示</h3>
          <ul className="terminal-list">
          {Object.entries(riskFlags).map(([key, value]) => (
            <li key={key}>
              {RISK_LABELS[key] ?? key}: {RISK_VALUE_LABELS[value] ?? value}
            </li>
          ))}
          </ul>
        </section>
        <PatternScoreCard
          score={patternInsight.status === "ready" ? patternInsight.data.score : null}
          loading={patternInsight.status === "loading"}
        />
        {groupStat === undefined ? null : (
          <section className="terminal-stack">
            <h3>相似样本统计</h3>
            <ul className="terminal-list">
            <li>相似样本数 {groupStat.sample_count ?? 0}</li>
            <li>1日均值 <span className={getMarketValueClass(groupStat.future_1d_mean)}>{formatSignedPercent(groupStat.future_1d_mean)}</span></li>
            <li>1日中位数 <span className={getMarketValueClass(groupStat.future_1d_median)}>{formatSignedPercent(groupStat.future_1d_median)}</span></li>
            <li>1日胜率 {formatPercent(groupStat.future_1d_win_rate)}</li>
            <li>3日均值 <span className={getMarketValueClass(groupStat.future_3d_mean)}>{formatSignedPercent(groupStat.future_3d_mean)}</span></li>
            <li>5日均值 <span className={getMarketValueClass(groupStat.future_5d_mean)}>{formatSignedPercent(groupStat.future_5d_mean)}</span></li>
            <li>10日均值 <span className={getMarketValueClass(groupStat.future_10d_mean)}>{formatSignedPercent(groupStat.future_10d_mean)}</span></li>
            </ul>
          </section>
        )}
        <SimilarCaseList
          items={similarCases}
          currentChartWindow={currentChartWindow}
          loadSegmentChartWindow={(segmentId) => apiClient.getSegmentChartWindow(String(segmentId))}
        />
      </div>
    </aside>
  );
}
