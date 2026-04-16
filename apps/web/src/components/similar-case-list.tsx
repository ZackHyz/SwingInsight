"use client";

import type { PatternSimilarCaseData } from "../lib/api";
import { getMarketValueClass } from "../lib/market-tone";

type SimilarCaseListProps = {
  items: PatternSimilarCaseData[];
  selectedCaseId?: number | null;
  onSelectCase?: (windowId: number) => void;
  currentStockCode?: string;
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

export function SimilarCaseList({ items, selectedCaseId = null, onSelectCase, currentStockCode = "" }: SimilarCaseListProps) {
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
      <p className="terminal-copy">按排序模式输出的历史窗口列表，用于核对 5/10/20 日后表现与同/跨标的差异。</p>
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
                <span className={getMarketValueClass(item.future_return_10d)}>{formatForwardReturn(item.future_return_10d)}</span> · 20日{" "}
                <span className={getMarketValueClass(item.future_return_20d)}>{formatForwardReturn(item.future_return_20d)}</span>
              </div>
              <div>
                样本股票 {item.stock_code ?? "--"} · 波段ID {item.segment_id ?? "--"} ·{" "}
                {item.stock_code !== undefined && item.stock_code !== null && item.stock_code === currentStockCode ? "同标的" : "跨标的"}
              </div>
              {item.window_id === undefined || onSelectCase === undefined ? null : (
                <button
                  className="terminal-button"
                  type="button"
                  onClick={() => onSelectCase(item.window_id as number)}
                >
                  {selectedCaseId === item.window_id ? "已选中" : "打开对比"}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
