import type { PatternScoreData } from "../lib/api";
import { getMarketValueClass } from "../lib/market-tone";

type PatternScoreCardProps = {
  score: PatternScoreData | null;
  loading?: boolean;
};

function formatPercent(value?: number) {
  if (value === undefined || value === null) {
    return "--";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatSignedPercent(value?: number) {
  if (value === undefined || value === null) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

const CONFIDENCE_LABELS: Record<PatternScoreData["confidence"], string> = {
  low: "低置信度",
  medium: "中置信度",
  high: "高置信度",
};

export function PatternScoreCard({ score, loading = false }: PatternScoreCardProps) {
  if (loading) {
    return (
      <section className="terminal-stack">
        <h3>形态评分</h3>
        <p className="terminal-copy">正在计算相似形态历史统计...</p>
      </section>
    );
  }
  if (score === null) {
    return (
      <section className="terminal-stack">
        <h3>形态评分</h3>
        <p className="terminal-copy">暂无可用的形态统计样本。</p>
      </section>
    );
  }
  return (
    <section className="terminal-stack">
      <h3>形态评分</h3>
      <ul className="terminal-list">
        <li>5日胜率 {formatPercent(score.win_rate_5d ?? score.win_rate)}</li>
        <li>10日胜率 {formatPercent(score.win_rate_10d ?? score.win_rate)}</li>
        <li>
          {score.horizon_days}日预期涨跌{" "}
          <span className={getMarketValueClass(score.avg_return)}>{formatSignedPercent(score.avg_return)}</span>
        </li>
        {score.raw_win_rate !== undefined ? <li>原始胜率 {formatPercent(score.raw_win_rate)}</li> : null}
        <li>样本数 n={score.sample_count}</li>
        <li>置信度 {CONFIDENCE_LABELS[score.confidence]}</li>
        <li>概率校准 {score.calibrated ? "已启用(Platt)" : "未启用"}</li>
      </ul>
    </section>
  );
}
