import { SimilarCaseList } from "./similar-case-list";
import { PatternScoreCard } from "./pattern-score-card";
import { OutcomeDistribution } from "./outcome-distribution";
import type { ApiClient, PatternSimilarCaseData, StockResearchData } from "../lib/api";
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
  const fallbackSimilarCases: PatternSimilarCaseData[] = (currentState.similar_cases ?? []).map((item) => ({
    window_id: item.window_id,
    window_start_date: item.window_start_date ?? item.start_date ?? null,
    window_end_date: item.window_end_date ?? item.end_date ?? null,
    segment_start_date: item.segment_start_date ?? item.start_date ?? null,
    segment_end_date: item.segment_end_date ?? item.end_date ?? null,
    similarity_score: item.score,
        future_return_5d: item.return_5d,
        future_return_10d: item.return_10d,
        future_return_20d: item.return_20d,
        stock_code: item.stock_code,
        segment_id: item.segment_id,
      }));
  const similarCases = patternInsight.status === "ready" ? patternInsight.data.similarCases : fallbackSimilarCases;
  const selectedCase = similarCases.find((item) => item.window_id === patternInsight.selectedCaseId) ?? null;
  const groupStat = currentState.group_stat;

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
        <OutcomeDistribution
          groupStat={patternInsight.status === "ready" ? patternInsight.data.groupStat : null}
          loading={patternInsight.status === "loading"}
          selectedReturnsByHorizon={{
            5: selectedCase?.future_return_5d ?? null,
            10: selectedCase?.future_return_10d ?? null,
            20: selectedCase?.future_return_20d ?? null,
          }}
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
          selectedCaseId={patternInsight.selectedCaseId}
          onSelectCase={patternInsight.setSelectedCaseId}
        />
      </div>
    </aside>
  );
}
