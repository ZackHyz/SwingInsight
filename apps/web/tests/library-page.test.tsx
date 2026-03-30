// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import LibraryPage from "../src/app/library/page";
import type { SegmentLibraryData } from "../src/lib/api";

function buildData(): SegmentLibraryData {
  return {
    rows: [
      {
        id: 1,
        stock_code: "000001",
        segment_type: "up_swing",
        label_names: ["放量突破型", "消息刺激型"],
        pct_change: 20.4545,
        duration_days: 4,
      },
      {
        id: 2,
        stock_code: "000002",
        segment_type: "down_swing",
        label_names: ["高位见顶型"],
        pct_change: -10.2,
        duration_days: 3,
      },
    ],
  };
}

describe("library page", () => {
  afterEach(() => cleanup());

  it("filters rows by stock code and label", () => {
    render(<LibraryPage initialData={buildData()} />);

    expect(screen.getByText("000001")).toBeTruthy();
    expect(screen.getByText("000002")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("股票代码过滤"), { target: { value: "000001" } });
    fireEvent.change(screen.getByLabelText("标签过滤"), { target: { value: "放量突破型" } });

    expect(screen.getByText("000001")).toBeTruthy();
    expect(screen.queryByText("000002")).toBeNull();
  });
});
