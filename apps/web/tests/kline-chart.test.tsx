// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KlineChart } from "../src/components/kline-chart";

describe("kline chart", () => {
  afterEach(() => cleanup());

  it("renders candlesticks and visible turning point markers", () => {
    const onSelectPrice = vi.fn();

    render(
      <KlineChart
        prices={[
          { trade_date: "2025-03-31", open_price: 5.1, high_price: 5.4, low_price: 4.9, close_price: 5.3, volume: 100000 },
          { trade_date: "2025-04-01", open_price: 5.3, high_price: 5.5, low_price: 5.0, close_price: 5.1, volume: 80000 },
          { trade_date: "2025-04-02", open_price: 5.1, high_price: 5.6, low_price: 5.0, close_price: 5.5, volume: 140000 },
        ]}
        autoPoints={[{ point_date: "2025-04-01", point_type: "peak", point_price: 5.5, source_type: "system" }]}
        provisionalPoints={[{ point_date: "2025-03-31", point_type: "trough", point_price: 4.9, source_type: "system" }]}
        finalPoints={[{ point_date: "2025-04-02", point_type: "peak", point_price: 5.6, source_type: "manual" }]}
        onSelectPrice={onSelectPrice}
      />
    );

    expect(screen.getByRole("button", { name: "放大" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "缩小" })).toBeTruthy();
    expect(screen.getByLabelText("窗口起点")).toBeTruthy();
    const candlesticks = screen.getAllByTestId("candlestick-body");
    expect(candlesticks).toHaveLength(3);
    expect(candlesticks[0].getAttribute("fill")).toBe("#ff6a7a");
    expect(candlesticks[1].getAttribute("fill")).toBe("#31d0a0");
    const volumeBars = screen.getAllByTestId("volume-bar");
    expect(volumeBars).toHaveLength(3);
    expect(volumeBars[0].getAttribute("fill")).toBe("#ff6a7a");
    expect(volumeBars[1].getAttribute("fill")).toBe("#31d0a0");

    const markers = screen.getAllByTestId("turning-point-marker");
    expect(markers).toHaveLength(2);
    expect(markers[0].tagName.toLowerCase()).toBe("polygon");
    expect(markers[0].getAttribute("fill")).toBe("#ff6a7a");
    expect(markers[1].tagName.toLowerCase()).toBe("polygon");
    expect(markers[1].getAttribute("fill")).toBe("#ffb85c");
    const provisionalMarkers = screen.getAllByTestId("provisional-turning-point-marker");
    expect(provisionalMarkers).toHaveLength(1);
    expect(provisionalMarkers[0].getAttribute("fill")).toBe("rgba(111, 182, 255, 0.12)");
    expect(screen.getByText("候选高点/低点，尚未确认反转")).toBeTruthy();

    fireEvent.click(screen.getByTestId("kline-canvas"), { clientX: 460, clientY: 100 });
    expect(onSelectPrice).toHaveBeenCalledTimes(1);
  });

  it("renders readonly chart without zoom controls and highlights the sample segment", () => {
    render(
      <KlineChart
        title="样本局部K线"
        mode="readonly"
        prices={[
          { trade_date: "2025-03-28", open_price: 5.0, high_price: 5.3, low_price: 4.9, close_price: 5.2, volume: 70000 },
          { trade_date: "2025-03-31", open_price: 5.2, high_price: 5.4, low_price: 5.1, close_price: 5.3, volume: 80000 },
          { trade_date: "2025-04-01", open_price: 5.3, high_price: 5.6, low_price: 5.2, close_price: 5.5, volume: 120000 },
          { trade_date: "2025-04-02", open_price: 5.5, high_price: 5.7, low_price: 5.4, close_price: 5.6, volume: 130000 },
        ]}
        autoPoints={[{ point_date: "2025-04-01", point_type: "peak", point_price: 5.6, source_type: "system" }]}
        finalPoints={[{ point_date: "2025-03-31", point_type: "trough", point_price: 5.1, source_type: "manual" }]}
        highlightRange={{ start_date: "2025-03-31", end_date: "2025-04-01" }}
      />
    );

    expect(screen.getByText("样本局部K线")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "放大" })).toBeNull();
    expect(screen.queryByRole("button", { name: "缩小" })).toBeNull();
    expect(screen.queryByLabelText("窗口起点")).toBeNull();
    expect(screen.getByTestId("segment-highlight")).toBeTruthy();
  });
});
