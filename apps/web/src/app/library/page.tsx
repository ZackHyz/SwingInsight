"use client";

import { useEffect, useMemo, useState } from "react";

import { AppShell } from "../../components/app-shell";
import { StatusPill } from "../../components/status-pill";
import { TerminalPanel } from "../../components/terminal-panel";
import { SegmentFilterBar } from "../../components/segment-filter-bar";
import { SegmentTable } from "../../components/segment-table";
import { apiClient, type ApiClient, type SegmentLibraryData } from "../../lib/api";

type LibraryPageProps = {
  initialData?: SegmentLibraryData;
  apiClient?: ApiClient;
};

export default function LibraryPage({ initialData, apiClient: client }: LibraryPageProps) {
  const api = client ?? apiClient;
  const [data, setData] = useState<SegmentLibraryData | null>(initialData ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [stockCode, setStockCode] = useState("");
  const [segmentType, setSegmentType] = useState("");
  const [label, setLabel] = useState("");

  useEffect(() => {
    if (initialData !== undefined) {
      setData(initialData);
      setLoadError(null);
      return;
    }
    if (api.getSegmentLibrary === undefined) {
      setData(null);
      setLoadError("当前环境未提供形态库接口。");
      return;
    }

    let cancelled = false;
    setData(null);
    setLoadError(null);
    api
      .getSegmentLibrary()
      .then((nextData) => {
        if (!cancelled) {
          setData(nextData);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load segment library";
          setLoadError(message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, initialData]);

  const rows = useMemo(() => {
    return (data?.rows ?? []).filter((row) => {
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
  }, [data?.rows, label, segmentType, stockCode]);

  const activeFilterCount = [stockCode, segmentType, label].filter((value) => value !== "").length;
  const totalRows = data?.rows.length ?? 0;
  const isLoading = data === null && loadError === null;

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
        {isLoading ? (
          <p className="terminal-copy">正在加载形态库...</p>
        ) : loadError !== null ? (
          <p className="terminal-copy">加载形态库失败: {loadError}</p>
        ) : (
          <div className="terminal-inline-metrics">
            <div className="metric-card">
              <p className="metric-card__eyebrow">当前可见</p>
              <p className="metric-card__value">{rows.length}</p>
            </div>
            <div className="metric-card">
              <p className="metric-card__eyebrow">总样本数</p>
              <p className="metric-card__value">{totalRows}</p>
            </div>
            <div className="metric-card">
              <p className="metric-card__eyebrow">已启用筛选</p>
              <p className="metric-card__value">{activeFilterCount}</p>
            </div>
          </div>
        )}
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
          {isLoading ? (
            <p className="terminal-copy">样本同步中...</p>
          ) : loadError !== null ? (
            <p className="terminal-copy">当前无法加载形态库: {loadError}</p>
          ) : rows.length === 0 ? (
            <p className="terminal-copy">当前没有可展示的形态样本。</p>
          ) : (
            <SegmentTable rows={rows} />
          )}
        </TerminalPanel>
      </section>
    </AppShell>
  );
}
