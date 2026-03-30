"use client";

import { useMemo, useState } from "react";

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

  return (
    <main>
      <h1>样本库</h1>
      <SegmentFilterBar
        stockCode={stockCode}
        segmentType={segmentType}
        label={label}
        onStockCodeChange={setStockCode}
        onSegmentTypeChange={setSegmentType}
        onLabelChange={setLabel}
      />
      <SegmentTable rows={rows} />
    </main>
  );
}
