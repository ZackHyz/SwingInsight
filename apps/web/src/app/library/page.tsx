"use client";

import { useMemo, useState } from "react";

import { AppShell } from "../../components/app-shell";
import { StatusPill } from "../../components/status-pill";
import { TerminalPanel } from "../../components/terminal-panel";
import { SegmentFilterBar } from "../../components/segment-filter-bar";
import { SegmentTable } from "../../components/segment-table";
import { type SegmentLibraryData } from "../../lib/api";

type LibraryPageProps = {
  initialData?: SegmentLibraryData;
};

function buildFallbackData(): SegmentLibraryData {
  return { rows: [] };
}

export default function LibraryPage({ initialData }: LibraryPageProps) {
  const data = initialData ?? buildFallbackData();
  const [stockCode, setStockCode] = useState("");
  const [segmentType, setSegmentType] = useState("");
  const [label, setLabel] = useState("");

  const rows = useMemo(() => {
    return data.rows.filter((row) => {
      if (stockCode && !row.stock_code.includes(stockCode)) {
        return false;
      }
      if (segmentType && !(row.segment_type ?? "").includes(segmentType)) {
        return false;
      }
      if (label && !row.label_names.some((item) => item.includes(label))) {
        return false;
      }
      return true;
    });
  }, [data.rows, label, segmentType, stockCode]);

  const activeFilterCount = [stockCode, segmentType, label].filter((value) => value !== "").length;

  return (
    <AppShell
      currentPath="/library"
      title="形态库"
      subtitle="检索历史波段、筛选标签，并在同一终端壳层里继续下钻候选样本。"
      topBarContent={
        <>
          <StatusPill label={`结果 ${rows.length}`} />
          <StatusPill label={`筛选 ${activeFilterCount}`} tone={activeFilterCount > 0 ? "warning" : "default"} />
        </>
      }
    >
      <TerminalPanel title="结果概览" eyebrow="形态库总览">
        <div className="terminal-inline-metrics">
          <div className="metric-card">
            <p className="metric-card__eyebrow">当前可见</p>
            <p className="metric-card__value">{rows.length}</p>
          </div>
          <div className="metric-card">
            <p className="metric-card__eyebrow">总样本数</p>
            <p className="metric-card__value">{data.rows.length}</p>
          </div>
          <div className="metric-card">
            <p className="metric-card__eyebrow">已启用筛选</p>
            <p className="metric-card__value">{activeFilterCount}</p>
          </div>
        </div>
      </TerminalPanel>

      <section className="terminal-grid terminal-grid--split">
        <TerminalPanel title="筛选条件" eyebrow="检索控制">
          <SegmentFilterBar
            stockCode={stockCode}
            segmentType={segmentType}
            label={label}
            onStockCodeChange={setStockCode}
            onSegmentTypeChange={setSegmentType}
            onLabelChange={setLabel}
          />
        </TerminalPanel>

        <TerminalPanel title="形态表格" eyebrow="分析视图">
          <SegmentTable rows={rows} />
        </TerminalPanel>
      </section>
    </AppShell>
  );
}
