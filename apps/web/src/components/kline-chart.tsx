import { useMemo, useState, type MouseEvent, type WheelEvent } from "react";

import type { PriceRow, StockPoint } from "../lib/api";

const MARKET_UP_FILL = "#ff6a7a";
const MARKET_UP_STROKE = "#ffd8de";
const MARKET_DOWN_FILL = "#31d0a0";
const MARKET_DOWN_STROKE = "#d8fff2";
const MANUAL_POINT_FILL = "#ffb85c";

type HighlightRange = {
  start_date: string;
  end_date: string;
};

type KlineChartProps = {
  title?: string | null;
  mode?: "interactive" | "readonly";
  prices: PriceRow[];
  autoPoints: StockPoint[];
  finalPoints: StockPoint[];
  onSelectPrice?: (row: PriceRow) => void;
  highlightRange?: HighlightRange;
  width?: number;
  height?: number;
};

type PriceScale = {
  min: number;
  max: number;
  span: number;
};

function buildPriceScale(prices: PriceRow[]): PriceScale {
  if (prices.length === 0) {
    return {
      min: 0,
      max: 1,
      span: 1,
    };
  }
  const lows = prices.map((row) => row.low_price);
  const highs = prices.map((row) => row.high_price);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  return {
    min,
    max,
    span: max - min || 1,
  };
}

function mapPriceY(price: number, height: number, scale: PriceScale): number {
  return height - ((price - scale.min) / scale.span) * height;
}

function buildPointLookup(points: StockPoint[]): Map<string, StockPoint> {
  return new Map(points.map((point) => [point.point_date, point]));
}

function buildTrianglePoints(centerX: number, centerY: number, pointType: StockPoint["point_type"]): string {
  if (pointType === "peak") {
    return `${centerX},${centerY + 8} ${centerX - 7},${centerY - 5} ${centerX + 7},${centerY - 5}`;
  }
  return `${centerX},${centerY - 8} ${centerX - 7},${centerY + 5} ${centerX + 7},${centerY + 5}`;
}

function formatVolume(volume: number): string {
  return new Intl.NumberFormat("zh-CN").format(Math.round(volume));
}

function resolvePointFill(point: StockPoint): string {
  if (point.source_type === "manual") {
    return MANUAL_POINT_FILL;
  }
  return point.point_type === "peak" ? MARKET_UP_FILL : MARKET_DOWN_FILL;
}

function resolvePointStroke(point: StockPoint): string {
  return point.point_type === "peak" ? MARKET_UP_STROKE : MARKET_DOWN_STROKE;
}

export function KlineChart({
  title = "日线研究图",
  mode = "interactive",
  prices,
  autoPoints,
  finalPoints,
  onSelectPrice,
  highlightRange,
  width = 1120,
  height = 640,
}: KlineChartProps) {
  const interactive = mode === "interactive";
  const plotPadding = { top: 28, right: 48, bottom: 56, left: 72 };
  const plotWidth = width - plotPadding.left - plotPadding.right;
  const volumeAreaHeight = interactive ? 240 : 120;
  const plotHeight = height - plotPadding.top - plotPadding.bottom - volumeAreaHeight;
  const volumeTop = plotPadding.top + plotHeight + 28;
  const [visibleCount, setVisibleCount] = useState(() => Math.max(Math.min(45, prices.length), 1));
  const [windowStart, setWindowStart] = useState(() => Math.max(prices.length - Math.min(45, prices.length), 0));
  const resolvedVisibleCount = interactive ? Math.min(Math.max(visibleCount, 1), Math.max(prices.length, 1)) : prices.length;
  const maxWindowStart = interactive ? Math.max(prices.length - resolvedVisibleCount, 0) : 0;
  const clampedWindowStart = interactive ? Math.min(windowStart, maxWindowStart) : 0;
  const visiblePrices = useMemo(
    () => (interactive ? prices.slice(clampedWindowStart, clampedWindowStart + resolvedVisibleCount) : prices),
    [clampedWindowStart, interactive, prices, resolvedVisibleCount]
  );
  const scale = buildPriceScale(visiblePrices);
  const candleWidth = Math.max(8, Math.floor(plotWidth / Math.max(visiblePrices.length, 1) / 1.8));
  const autoPointLookup = buildPointLookup(autoPoints);
  const finalPointLookup = buildPointLookup(finalPoints);
  const priceTicks = [1, 0.75, 0.5, 0.25, 0].map((ratio) => scale.min + scale.span * ratio);
  const maxVolume = Math.max(...visiblePrices.map((row) => row.volume ?? 0), 1);
  const midVolume = maxVolume / 2;
  const dateLabelIndexes =
    visiblePrices.length === 0
      ? []
      : Array.from(new Set([0, Math.floor((visiblePrices.length - 1) / 2), visiblePrices.length - 1])).filter((index) => index >= 0);
  const highlightRect = useMemo(() => {
    if (highlightRange === undefined || visiblePrices.length === 0) {
      return null;
    }
    const startIndex = visiblePrices.findIndex((row) => row.trade_date === highlightRange.start_date);
    const endIndex = visiblePrices.findIndex((row) => row.trade_date === highlightRange.end_date);
    if (startIndex === -1 || endIndex === -1) {
      return null;
    }
    const leftIndex = Math.min(startIndex, endIndex);
    const rightIndex = Math.max(startIndex, endIndex);
    const step = plotWidth / Math.max(visiblePrices.length, 1);
    return {
      x: plotPadding.left + step * leftIndex,
      width: step * (rightIndex - leftIndex + 1),
    };
  }, [highlightRange, plotWidth, visiblePrices]);

  function handleClick(event: MouseEvent<SVGSVGElement>) {
    if (!interactive || onSelectPrice === undefined || visiblePrices.length === 0) {
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = Math.max(0, event.clientX - rect.left);
    const normalizedX = rect.width > 0 ? relativeX / rect.width : 0;
    const plotLeft = plotPadding.left / width;
    const plotRight = (plotPadding.left + plotWidth) / width;
    const constrainedRatio = Math.min(1, Math.max(0, (normalizedX - plotLeft) / Math.max(plotRight - plotLeft, 0.001)));
    const ratio = constrainedRatio;
    const index = Math.min(visiblePrices.length - 1, Math.max(0, Math.round(ratio * (visiblePrices.length - 1))));
    onSelectPrice(visiblePrices[index]);
  }

  function updateWindow(nextVisibleCount: number, anchorRatio = 1) {
    if (!interactive) {
      return;
    }
    const boundedVisibleCount = Math.min(prices.length, Math.max(20, nextVisibleCount));
    const anchorIndex = clampedWindowStart + Math.round((resolvedVisibleCount - 1) * anchorRatio);
    const nextWindowStart = Math.max(
      0,
      Math.min(prices.length - boundedVisibleCount, anchorIndex - Math.round((boundedVisibleCount - 1) * anchorRatio))
    );
    setVisibleCount(boundedVisibleCount);
    setWindowStart(nextWindowStart);
  }

  function zoomIn() {
    updateWindow(visibleCount - 10);
  }

  function zoomOut() {
    updateWindow(visibleCount + 10);
  }

  function handleWheel(event: WheelEvent<SVGSVGElement>) {
    if (!interactive || visiblePrices.length === 0) {
      return;
    }
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    const normalizedX = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 1;
    const plotLeft = plotPadding.left / width;
    const plotRight = (plotPadding.left + plotWidth) / width;
    const anchorRatio = Math.min(1, Math.max(0, (normalizedX - plotLeft) / Math.max(plotRight - plotLeft, 0.001)));
    if (event.deltaY < 0) {
      updateWindow(visibleCount - 10, anchorRatio);
      return;
    }
    updateWindow(visibleCount + 10, anchorRatio);
  }

  return (
    <section className="terminal-stack">
      {title === null ? null : <h2>{title}</h2>}
      {interactive ? (
        <div className="kline-controls terminal-button-row">
          <button className="terminal-button" type="button" onClick={zoomIn} disabled={resolvedVisibleCount <= 20}>
            放大
          </button>
          <button className="terminal-button" type="button" onClick={zoomOut} disabled={resolvedVisibleCount >= prices.length}>
            缩小
          </button>
          <label className="terminal-field">
            窗口起点
            <input
              type="range"
              aria-label="窗口起点"
              min="0"
              max={String(maxWindowStart)}
              value={clampedWindowStart}
              onChange={(event) => setWindowStart(Number(event.target.value))}
            />
          </label>
          <span>
            显示 {clampedWindowStart + 1}-{Math.min(clampedWindowStart + resolvedVisibleCount, prices.length)} / {prices.length}
          </span>
        </div>
      ) : null}
      {visiblePrices.length === 0 ? <p>暂无可绘制的K线数据。</p> : null}
      <svg
        data-testid="kline-canvas"
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={title ?? "K线图"}
        onClick={interactive ? handleClick : undefined}
        onWheel={interactive ? handleWheel : undefined}
        style={{
          width: "100%",
          height: "auto",
          display: "block",
          background: "#050917",
          border: "1px solid rgba(140, 161, 255, 0.16)",
          borderRadius: 16,
          boxShadow: "0 18px 45px rgba(0, 0, 0, 0.3)",
        }}
      >
        <rect x={plotPadding.left} y={plotPadding.top} width={plotWidth} height={plotHeight} fill="#0a1328" rx="12" />
        <rect x={plotPadding.left} y={volumeTop} width={plotWidth} height={volumeAreaHeight} fill="#09101f" rx="12" />
        {highlightRect === null ? null : (
          <>
            <rect
              data-testid="segment-highlight"
              x={highlightRect.x}
              y={plotPadding.top}
              width={highlightRect.width}
              height={plotHeight}
              fill="#8b7dff"
              opacity="0.12"
              rx="10"
            />
            <rect
              x={highlightRect.x}
              y={volumeTop}
              width={highlightRect.width}
              height={volumeAreaHeight}
              fill="#8b7dff"
              opacity="0.1"
              rx="10"
            />
          </>
        )}
        {priceTicks.map((value) => {
          const y = plotPadding.top + mapPriceY(value, plotHeight, scale);
          return (
            <g key={value.toFixed(2)}>
              <line
                x1={plotPadding.left}
                y1={y}
                x2={plotPadding.left + plotWidth}
                y2={y}
                stroke="rgba(148, 163, 200, 0.3)"
                strokeDasharray="6 6"
                strokeWidth="1"
              />
              <text x={plotPadding.left - 10} y={y + 4} textAnchor="end" fontSize="12" fill="#94a3b8">
                {value.toFixed(2)}
              </text>
            </g>
          );
        })}
        {visiblePrices.map((row, index) => {
          const step = plotWidth / Math.max(visiblePrices.length, 1);
          const centerX = plotPadding.left + step * index + step / 2;
          const openY = plotPadding.top + mapPriceY(row.open_price, plotHeight, scale);
          const closeY = plotPadding.top + mapPriceY(row.close_price, plotHeight, scale);
          const highY = plotPadding.top + mapPriceY(row.high_price, plotHeight, scale);
          const lowY = plotPadding.top + mapPriceY(row.low_price, plotHeight, scale);
          const candleTop = Math.min(openY, closeY);
          const candleHeight = Math.max(Math.abs(openY - closeY), 2);
          const rising = row.close_price >= row.open_price;
          const volumeRatio = (row.volume ?? 0) / maxVolume;
          const volumeHeight = Math.max(volumeRatio * (volumeAreaHeight - 28), 2);
          const autoPoint = autoPointLookup.get(row.trade_date);
          const finalPoint = finalPointLookup.get(row.trade_date);

          return (
            <g key={row.trade_date}>
              <line
                x1={centerX}
                y1={highY}
                x2={centerX}
                y2={lowY}
                stroke={rising ? MARKET_UP_FILL : MARKET_DOWN_FILL}
                strokeWidth="1.5"
              />
              <rect
                data-testid="candlestick-body"
                x={centerX - candleWidth / 2}
                y={candleTop}
                width={candleWidth}
                height={candleHeight}
                fill={rising ? MARKET_UP_FILL : MARKET_DOWN_FILL}
                stroke={rising ? MARKET_UP_STROKE : MARKET_DOWN_STROKE}
                strokeWidth="1.5"
                rx="1"
              />
              {autoPoint === undefined ? null : (
                <polygon
                  data-testid="turning-point-marker"
                  points={buildTrianglePoints(
                    centerX,
                    plotPadding.top + mapPriceY(autoPoint.point_price, plotHeight, scale),
                    autoPoint.point_type
                  )}
                  fill={resolvePointFill(autoPoint)}
                  stroke={resolvePointStroke(autoPoint)}
                  strokeWidth="1.8"
                />
              )}
              {finalPoint === undefined ? null : (
                <polygon
                  data-testid="turning-point-marker"
                  points={buildTrianglePoints(
                    centerX,
                    plotPadding.top + mapPriceY(finalPoint.point_price, plotHeight, scale),
                    finalPoint.point_type
                  )}
                  fill={resolvePointFill(finalPoint)}
                  stroke={resolvePointStroke(finalPoint)}
                  strokeWidth="1.5"
                />
              )}
              <rect
                data-testid="volume-bar"
                x={centerX - candleWidth / 2}
                y={volumeTop + volumeAreaHeight - volumeHeight}
                width={candleWidth}
                height={volumeHeight}
                fill={rising ? MARKET_UP_FILL : MARKET_DOWN_FILL}
                opacity="0.9"
                rx="1"
              />
            </g>
          );
        })}
        {dateLabelIndexes.map((index) => {
          const row = visiblePrices[index];
          const step = plotWidth / Math.max(visiblePrices.length, 1);
          const centerX = plotPadding.left + step * index + step / 2;
          return (
            <text key={row.trade_date} x={centerX} y={height - 18} textAnchor="middle" fontSize="12" fill="#94a3b8">
              {row.trade_date.slice(5)}
            </text>
          );
        })}
        {interactive ? (
          <text x={plotPadding.left} y="18" fontSize="13" fill="#94a3b8">
            滚轮缩放，滑块平移
          </text>
        ) : null}
        <text x={plotPadding.left} y={volumeTop - 8} fontSize="12" fill="#94a3b8">
          成交量（真实数量，单位：股）
        </text>
        <text x={plotPadding.left - 10} y={volumeTop + 10} textAnchor="end" fontSize="12" fill="#94a3b8">
          {formatVolume(maxVolume)}
        </text>
        <text x={plotPadding.left - 10} y={volumeTop + volumeAreaHeight / 2 + 4} textAnchor="end" fontSize="12" fill="#94a3b8">
          {formatVolume(midVolume)}
        </text>
        <text x={plotPadding.left - 10} y={volumeTop + volumeAreaHeight} textAnchor="end" fontSize="12" fill="#94a3b8">
          0
        </text>
      </svg>
      {interactive ? (
        <div className="terminal-button-row" style={{ color: "#94a3b8" }}>
          <span>自动拐点: {autoPoints.length}</span>
          <span>最终拐点: {finalPoints.length}</span>
          <span>红K=上涨</span>
          <span>绿K=下跌</span>
          <span>红三角=系统波峰</span>
          <span>绿三角=系统波谷</span>
          <span>下方柱=成交量</span>
          <span>黄三角=手动标记</span>
          {highlightRange === undefined ? null : <span>橙色高亮=样本波段</span>}
        </div>
      ) : null}
    </section>
  );
}
