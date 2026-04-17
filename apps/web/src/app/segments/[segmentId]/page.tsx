"use client";

import { AppShell } from "../../../components/app-shell";
import { NewsTimeline } from "../../../components/news-timeline";
import { StatusPill } from "../../../components/status-pill";
import { SegmentSummaryCard } from "../../../components/segment-summary-card";
import { TerminalPanel } from "../../../components/terminal-panel";
import { apiClient, type ApiClient, type SegmentDetailData } from "../../../lib/api";
import { getTrendTone } from "../../../lib/market-tone";

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
    <AppShell
      currentPath={`/segments/${segmentId}`}
      title={`波段 ${segmentId}`}
      subtitle="下钻查看选中形态波段，核对摘要指标并追踪相关事件。"
      topBarContent={
        <>
          <StatusPill label={`波段 ${pageData.segment.id}`} />
          <StatusPill label={pageData.segment.trend_direction === "up" ? "上行趋势" : "下行趋势"} tone={getTrendTone(pageData.segment.trend_direction)} />
        </>
      }
    >
      <TerminalPanel title="波段拆解" eyebrow="形态分析">
        <SegmentSummaryCard segment={pageData.segment} />
      </TerminalPanel>
      <NewsTimeline items={pageData.news_timeline} />
      <TerminalPanel title="标签面板" eyebrow="标签语境">
        <p className="terminal-copy">
          {pageData.labels.length === 0 ? "标签占位" : pageData.labels.map((label) => label.label_name).join(", ")}
        </p>
      </TerminalPanel>
    </AppShell>
  );
}
