// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import SegmentDetailPage from "../src/app/segments/[segmentId]/page";
import type { SegmentDetailData } from "../src/lib/api";

function buildData(): SegmentDetailData {
  return {
    segment: {
      id: 1,
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
    news_timeline: [
      {
        news_id: 11,
        title: "Bank support policy",
        summary: "Support before trough",
        source_name: "source-a",
        relation_type: "before_trough",
        distance_days: -2,
        news_date: "2024-01-02",
      },
      {
        news_id: 12,
        title: "Quarterly preview",
        summary: "Inside segment",
        source_name: "source-b",
        relation_type: "inside_segment",
        distance_days: 2,
        news_date: "2024-01-06",
      },
    ],
    labels: [],
  };
}

describe("segment detail page", () => {
  afterEach(() => cleanup());

  it("renders segment summary and news timeline", () => {
    render(
      <SegmentDetailPage
        segmentId="1"
        initialData={buildData()}
        apiClient={{ getStockResearch: vi.fn(), commitTurningPoints: vi.fn(), getSegmentDetail: vi.fn() }}
      />
    );

    expect(screen.getByText("000001 波段详情")).toBeTruthy();
    expect(screen.getByText("20.45%")).toBeTruthy();
    expect(screen.getByText("Bank support policy")).toBeTruthy();
    expect(screen.getByText("before_trough")).toBeTruthy();
  });
});
