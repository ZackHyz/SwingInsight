import { useEffect, useMemo, useState } from "react";

import type { PatternGroupStatData } from "../lib/api";

type OutcomeDistributionProps = {
  groupStat: PatternGroupStatData | null;
  loading?: boolean;
  step?: number;
  selectedReturn?: number | null;
  selectedReturnsByHorizon?: Partial<Record<number, number | null>>;
};

type HistogramBin = {
  left: number;
  right: number;
  count: number;
};

function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

function buildHistogram(values: number[], step: number): HistogramBin[] {
  if (values.length === 0) {
    return [];
  }
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const start = Math.floor(minValue / step) * step;
  const end = Math.ceil(maxValue / step) * step;
  const safeEnd = end <= start ? start + step : end;
  const bins: HistogramBin[] = [];
  for (let edge = start; edge < safeEnd; edge += step) {
    bins.push({ left: edge, right: edge + step, count: 0 });
  }
  for (const value of values) {
    const idx = Math.min(
      bins.length - 1,
      Math.max(0, Math.floor((value - start) / step)),
    );
    bins[idx].count += 1;
  }
  return bins;
}

export function OutcomeDistribution({
  groupStat,
  loading = false,
  step = 0.02,
  selectedReturn = null,
  selectedReturnsByHorizon,
}: OutcomeDistributionProps) {
  const horizons = useMemo(
    () =>
      groupStat?.horizon_days?.filter((horizon) => Number.isFinite(horizon) && horizon > 0) ?? [],
    [groupStat],
  );
  const defaultHorizon = horizons.includes(10) ? 10 : (horizons[0] ?? 10);
  const [activeHorizon, setActiveHorizon] = useState<number>(defaultHorizon);
  useEffect(() => {
    if (!horizons.includes(activeHorizon) && horizons.length > 0) {
      setActiveHorizon(defaultHorizon);
    }
  }, [activeHorizon, defaultHorizon, horizons]);

  if (loading) {
    return (
      <section className="terminal-stack">
        <h3>结果分布</h3>
        <p className="terminal-copy">正在加载分布数据...</p>
      </section>
    );
  }

  const distributionMap = groupStat?.return_distributions ?? {};
  const values = distributionMap[String(activeHorizon)] ?? (activeHorizon === 10 ? (groupStat?.return_distribution ?? []) : []);
  if (values.length === 0) {
    return (
      <section className="terminal-stack">
        <h3>结果分布</h3>
        <p className="terminal-copy">暂无可用分布数据。</p>
      </section>
    );
  }

  const bins = buildHistogram(values, step);
  const maxCount = Math.max(...bins.map((item) => item.count), 1);
  const horizonIndex = horizons.indexOf(activeHorizon);
  const predictionReturn = horizonIndex >= 0 ? (groupStat?.avg_returns?.[horizonIndex] ?? null) : null;
  const selectedValue = selectedReturnsByHorizon?.[activeHorizon] ?? selectedReturn;

  return (
    <section className="terminal-stack">
      <h3>结果分布</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {horizons.map((horizon) => (
          <button
            type="button"
            key={horizon}
            onClick={() => setActiveHorizon(horizon)}
            style={{
              border: "1px solid var(--terminal-border)",
              background: horizon === activeHorizon ? "var(--terminal-accent)" : "transparent",
              color: horizon === activeHorizon ? "var(--terminal-bg)" : "var(--terminal-ink)",
              padding: "2px 8px",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {horizon}d
          </button>
        ))}
      </div>
      <p className="terminal-copy">{activeHorizon}日后涨跌分布（每 {formatPercent(step)} 一档）</p>
      <div className="terminal-stack">
        {bins.map((bin) => {
          const widthPercent = (bin.count / maxCount) * 100;
          const markerInBin =
            predictionReturn !== null &&
            predictionReturn >= bin.left &&
            (predictionReturn < bin.right || (bin === bins[bins.length - 1] && predictionReturn <= bin.right));
          const isSelected =
            selectedValue !== null &&
            selectedValue >= bin.left &&
            (selectedValue < bin.right || (bin === bins[bins.length - 1] && selectedValue <= bin.right));
          return (
            <div key={`${bin.left}-${bin.right}`} style={{ display: "grid", gridTemplateColumns: "160px 1fr 44px", gap: 8, alignItems: "center" }}>
              <span>{`${formatPercent(bin.left)} ~ ${formatPercent(bin.right)}`}</span>
              <div style={{ width: "100%", background: "var(--terminal-border)", height: 10, borderRadius: 4 }}>
                <div
                  style={{
                    width: `${widthPercent}%`,
                    background: isSelected ? "#f59e0b" : "var(--terminal-accent)",
                    height: "100%",
                    borderRadius: 4,
                  }}
                />
              </div>
              <span style={{ textAlign: "right" }}>{isSelected ? `${bin.count} ●` : `${bin.count}`}{markerInBin ? " |" : ""}</span>
            </div>
          );
        })}
      </div>
      <p className="terminal-copy">
        当前预测落点: {predictionReturn === null ? "--" : formatPercent(predictionReturn)}
      </p>
    </section>
  );
}
