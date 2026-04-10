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
      title="Pattern Library"
      subtitle="Search historical segments, scan labels, and drill into candidates without leaving the terminal shell."
      topBarContent={
        <>
          <StatusPill label={`Rows ${rows.length}`} />
          <StatusPill label={`Active Filters ${activeFilterCount}`} tone={activeFilterCount > 0 ? "warning" : "default"} />
        </>
      }
    >
      <TerminalPanel title="Result Summary" eyebrow="Library Overview">
        <div className="terminal-inline-metrics">
          <div className="metric-card">
            <p className="metric-card__eyebrow">Visible Rows</p>
            <p className="metric-card__value">{rows.length}</p>
          </div>
          <div className="metric-card">
            <p className="metric-card__eyebrow">Total Rows</p>
            <p className="metric-card__value">{data.rows.length}</p>
          </div>
          <div className="metric-card">
            <p className="metric-card__eyebrow">Active Filters</p>
            <p className="metric-card__value">{activeFilterCount}</p>
          </div>
        </div>
      </TerminalPanel>

      <section className="terminal-grid terminal-grid--split">
        <TerminalPanel title="Filter Stack" eyebrow="Search Controls">
          <SegmentFilterBar
            stockCode={stockCode}
            segmentType={segmentType}
            label={label}
            onStockCodeChange={setStockCode}
            onSegmentTypeChange={setSegmentType}
            onLabelChange={setLabel}
          />
        </TerminalPanel>

        <TerminalPanel title="Pattern Grid" eyebrow="Analysis View">
          <SegmentTable rows={rows} />
        </TerminalPanel>
      </section>
    </AppShell>
  );
}
