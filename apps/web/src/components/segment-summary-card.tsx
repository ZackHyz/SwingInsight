import type { SegmentDetailData } from "../lib/api";
import { getMarketValueClass } from "../lib/market-tone";

type SegmentSummaryCardProps = {
  segment: SegmentDetailData["segment"];
};

function formatPct(value: number | null) {
  if (value === null) {
    return "--";
  }
  return `${value.toFixed(2)}%`;
}

export function SegmentSummaryCard({ segment }: SegmentSummaryCardProps) {
  return (
    <section className="terminal-stack">
      <div>
        <h2>{segment.stock_code} 波段详情</h2>
        <p className="terminal-copy">
          {segment.start_date} - {segment.end_date}
        </p>
      </div>
      <div className="terminal-inline-metrics">
        <div className="metric-card">
          <p className="metric-card__eyebrow">涨跌幅</p>
          <p className={`metric-card__value ${getMarketValueClass(segment.pct_change)}`}>{formatPct(segment.pct_change)}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__eyebrow">持续天数</p>
          <p className="metric-card__value">{segment.duration_days ?? 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__eyebrow">最大上涨</p>
          <p className={`metric-card__value ${getMarketValueClass(segment.max_upside_pct)}`}>{formatPct(segment.max_upside_pct)}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__eyebrow">最大回撤</p>
          <p className={`metric-card__value ${getMarketValueClass(segment.max_drawdown_pct)}`}>{formatPct(segment.max_drawdown_pct)}</p>
        </div>
        <div className="metric-card">
          <p className="metric-card__eyebrow">日均变化</p>
          <p className={`metric-card__value ${getMarketValueClass(segment.avg_daily_change_pct)}`}>{formatPct(segment.avg_daily_change_pct)}</p>
        </div>
      </div>
    </section>
  );
}
