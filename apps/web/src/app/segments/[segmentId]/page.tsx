"use client";

import { useEffect, useState } from "react";

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
  const client = props.apiClient ?? apiClient;
  const [pageData, setPageData] = useState<SegmentDetailData | null>(props.initialData ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (props.initialData !== undefined) {
      setPageData(props.initialData);
      setLoadError(null);
      return;
    }
    if (client.getSegmentDetail === undefined) {
      setPageData(null);
      setLoadError("当前环境未提供波段详情接口。");
      return;
    }

    let cancelled = false;
    setPageData(null);
    setLoadError(null);
    client
      .getSegmentDetail(segmentId)
      .then((nextData) => {
        if (!cancelled) {
          setPageData(nextData);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load segment detail";
          setLoadError(message);
          setPageData(buildFallbackData(segmentId));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [client, props.initialData, segmentId]);

  const resolvedPageData = pageData ?? buildFallbackData(segmentId);
  const isLoading = pageData === null && loadError === null;
  const labelSummary = resolvedPageData.labels.length === 0
    ? "当前波段未命中已命名形态"
    : resolvedPageData.labels.map((label) => label.label_name).join(" / ");

  return (
    <AppShell
      currentPath={`/segments/${segmentId}`}
      title={`波段 ${segmentId}`}
      subtitle="下钻查看选中形态波段，核对摘要指标并追踪相关事件。"
      topBarContent={
        <>
          <StatusPill label={`波段 ${resolvedPageData.segment.id}`} />
          <StatusPill
            label={resolvedPageData.segment.trend_direction === "up" ? "上行趋势" : "下行趋势"}
            tone={getTrendTone(resolvedPageData.segment.trend_direction)}
          />
        </>
      }
    >
      <TerminalPanel title="波段拆解" eyebrow="形态分析">
        {isLoading ? (
          <p className="terminal-copy">正在加载波段详情...</p>
        ) : loadError !== null ? (
          <p className="terminal-copy">加载波段详情失败: {loadError}</p>
        ) : (
          <SegmentSummaryCard segment={resolvedPageData.segment} />
        )}
      </TerminalPanel>
      <NewsTimeline items={resolvedPageData.news_timeline} />
      <TerminalPanel title="标签面板" eyebrow="标签语境">
        <p className="terminal-copy">{labelSummary}</p>
      </TerminalPanel>
    </AppShell>
  );
}
