"use client";

import type { PatternSimilarCaseData } from "../lib/api";
import { getMarketValueClass } from "../lib/market-tone";

type SimilarCaseListProps = {
  items: PatternSimilarCaseData[];
  selectedCaseId?: number | null;
  onSelectCase?: (windowId: number) => void;
};

function formatPercent(score?: number | null) {
  if (score === undefined || score === null) {
    return "--";
  }
  return `${(score * 100).toFixed(1)}%`;
}

function formatForwardReturn(value?: number | null) {
  if (value === undefined || value === null) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

export function SimilarCaseList({ items, selectedCaseId = null, onSelectCase }: SimilarCaseListProps) {
  if (items.length === 0) {
    return (
      <section className="terminal-stack">
        <h3>相似样本时间线</h3>
        <p className="terminal-copy">目前还没有可比样本。</p>
      </section>
    );
  }

  return (
    <section className="terminal-stack">
      <h3>相似样本时间线</h3>
      <p className="terminal-copy">按相似度排序的历史窗口列表，用于快速核对 5 日和 10 日后表现。</p>
      <ul className="terminal-list">
        {items.map((item) => (
          <li
            key={`${item.segment_id ?? "seg"}-${item.window_id ?? item.window_start_date ?? "case"}`}
            className="terminal-panel"
            style={{
              outline: selectedCaseId !== null && item.window_id === selectedCaseId ? "1px solid var(--terminal-accent)" : undefined,
            }}
          >
            <div className="terminal-panel__body">
              <div>
                窗口日期 {item.window_start_date ?? "--"} 至 {item.window_end_date ?? "--"} · 相似度 {formatPercent(item.similarity_score)}
              </div>
              <div>
                5日 <span className={getMarketValueClass(item.future_return_5d)}>{formatForwardReturn(item.future_return_5d)}</span> · 10日{" "}
                <span className={getMarketValueClass(item.future_return_10d)}>{formatForwardReturn(item.future_return_10d)}</span>
              </div>
              <div>样本股票 {item.stock_code ?? "--"} · 波段ID {item.segment_id ?? "--"}</div>
              {item.window_id === undefined || onSelectCase === undefined ? null : (
                <button
                  className="terminal-button"
                  type="button"
                  onClick={() => onSelectCase(item.window_id as number)}
                >
                  {selectedCaseId === item.window_id ? "已选中" : "选中样本"}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
