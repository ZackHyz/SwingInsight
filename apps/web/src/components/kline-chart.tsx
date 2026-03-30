import type { MouseEvent } from "react";

import type { PriceRow, StockPoint } from "../lib/api";

type KlineChartProps = {
  prices: PriceRow[];
  autoPoints: StockPoint[];
  finalPoints: StockPoint[];
  onSelectPrice: (row: PriceRow) => void;
};

function buildPolyline(prices: PriceRow[], width: number, height: number) {
  const closes = prices.map((row) => row.close_price);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = max - min || 1;

  return prices
    .map((row, index) => {
      const x = (index / Math.max(prices.length - 1, 1)) * width;
      const y = height - ((row.close_price - min) / span) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

export function KlineChart({ prices, autoPoints, finalPoints, onSelectPrice }: KlineChartProps) {
  const width = 480;
  const height = 240;

  function handleClick(event: MouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = Math.max(0, event.clientX - rect.left);
    const ratio = rect.width > 0 ? relativeX / rect.width : 0;
    const index = Math.min(prices.length - 1, Math.max(0, Math.round(ratio * (prices.length - 1))));
    onSelectPrice(prices[index]);
  }

  return (
    <section>
      <h2>日线研究图</h2>
      <svg
        data-testid="kline-canvas"
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="K line chart"
        onClick={handleClick}
      >
        <polyline fill="none" stroke="#0f766e" strokeWidth="3" points={buildPolyline(prices, width, height)} />
      </svg>
      <p>自动拐点: {autoPoints.length}</p>
      <p>最终拐点: {finalPoints.length}</p>
    </section>
  );
}
