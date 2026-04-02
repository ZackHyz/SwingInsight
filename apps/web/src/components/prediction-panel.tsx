import { SimilarCaseList } from "./similar-case-list";
import type { ApiClient, SegmentChartWindowData, StockResearchData } from "../lib/api";

type PredictionPanelProps = {
  apiClient: Pick<ApiClient, "getSegmentChartWindow">;
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
}: Pick<PredictionPanelProps, "stockCode" | "prices" | "autoPoints" | "finalPoints">): SegmentChartWindowData | null {
  if (prices.length === 0) {
    return null;
  }

  let windowStartIndex = Math.max(prices.length - (CONTEXT_TRADING_DAYS * 2 + 3), 0);
  let windowEndIndex = prices.length;
  let highlightStartDate = prices[Math.max(prices.length - 2, 0)].trade_date;
  let highlightEndDate = prices[prices.length - 1].trade_date;

  if (finalPoints.length >= 2) {
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

export function PredictionPanel({ apiClient, stockCode, prices, autoPoints, finalPoints, currentState }: PredictionPanelProps) {
  const probabilities = currentState.probabilities ?? {};
  const keyFeatures = currentState.key_features ?? {};
  const riskFlags = currentState.risk_flags ?? {};
  const similarCases = currentState.similar_cases ?? [];
  const currentChartWindow = buildCurrentChartWindow({ stockCode, prices, autoPoints, finalPoints });

  return (
    <aside>
      <h2>预测面板</h2>
      <p>当前状态: {currentState.label}</p>
      <p>{currentState.summary}</p>
      <section>
        <h3>方向概率</h3>
        <ul>
          {Object.entries(probabilities).map(([key, value]) => (
            <li key={key}>
              {PROBABILITY_LABELS[key] ?? key} {(value * 100).toFixed(1)}%
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>关键触发特征</h3>
        <ul>
          {Object.entries(keyFeatures).map(([key, value]) => (
            <li key={key}>
              {FEATURE_LABELS[key] ?? key} {value}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>风险提示</h3>
        <ul>
          {Object.entries(riskFlags).map(([key, value]) => (
            <li key={key}>
              {RISK_LABELS[key] ?? key}: {RISK_VALUE_LABELS[value] ?? value}
            </li>
          ))}
        </ul>
      </section>
      <SimilarCaseList
        items={similarCases}
        currentChartWindow={currentChartWindow}
        loadSegmentChartWindow={(segmentId) => apiClient.getSegmentChartWindow(String(segmentId))}
      />
    </aside>
  );
}
