import type { SegmentDetailData } from "../lib/api";

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
    <section>
      <h2>{segment.stock_code} 波段详情</h2>
      <p>
        {segment.start_date} - {segment.end_date}
      </p>
      <p>{formatPct(segment.pct_change)}</p>
      <p>持续 {segment.duration_days ?? 0} 天</p>
      <p>最大上涨 {formatPct(segment.max_upside_pct)}</p>
      <p>最大回撤 {formatPct(segment.max_drawdown_pct)}</p>
      <p>日均变化 {formatPct(segment.avg_daily_change_pct)}</p>
    </section>
  );
}
