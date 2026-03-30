"use client";

import { NewsTimeline } from "../../../components/news-timeline";
import { SegmentSummaryCard } from "../../../components/segment-summary-card";
import { apiClient, type ApiClient, type SegmentDetailData } from "../../../lib/api";

type SegmentDetailPageProps = {
  segmentId?: string;
  initialData?: SegmentDetailData;
  apiClient?: ApiClient;
};

function buildFallbackData(segmentId: string): SegmentDetailData {
  return {
    segment: {
      id: Number(segmentId),
      stock_code: "000001",
      trend_direction: "up",
      start_date: "2024-01-04",
      end_date: "2024-01-08",
      start_price: 8.8,
      end_price: 10.6,
      pct_change: 20.4545,
      duration_days: 4,
      max_drawdown_pct: -2.2727,
      max_upside_pct: 21.5909,
      avg_daily_change_pct: 6.8182,
    },
    news_timeline: [],
    labels: [],
  };
}

export default function SegmentDetailPage(props: SegmentDetailPageProps) {
  const segmentId = props.segmentId ?? "1";
  const pageData = props.initialData ?? buildFallbackData(segmentId);
  void (props.apiClient ?? apiClient);

  return (
    <main>
      <SegmentSummaryCard segment={pageData.segment} />
      <NewsTimeline items={pageData.news_timeline} />
      <section>
        <h2>波段标签</h2>
        <p>{pageData.labels.length === 0 ? "标签占位" : pageData.labels.map((label) => label.label_name).join(", ")}</p>
      </section>
    </main>
  );
}
