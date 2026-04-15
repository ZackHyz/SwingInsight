// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SimilarCaseList } from "../src/components/similar-case-list";

describe("similar case list", () => {
  afterEach(() => cleanup());

  it("renders empty state", () => {
    render(<SimilarCaseList items={[]} />);

    expect(screen.getByText("相似样本时间线")).toBeTruthy();
    expect(screen.getByText("目前还没有可比样本。")).toBeTruthy();
  });

  it("renders v1 static timeline rows", () => {
    const onSelectCase = vi.fn();
    render(
      <SimilarCaseList
        selectedCaseId={301}
        onSelectCase={onSelectCase}
        items={[
          {
            segment_id: 12,
            stock_code: "600157",
            window_id: 301,
            window_start_date: "2025-08-01",
            window_end_date: "2025-08-07",
            similarity_score: 0.8342,
            future_return_5d: 0.048,
            future_return_10d: -0.012,
          },
        ]}
      />
    );

    expect(screen.getByText("相似样本时间线")).toBeTruthy();
    expect(screen.getByText(/窗口日期 2025-08-01 至 2025-08-07 · 相似度 83.4%/)).toBeTruthy();
    expect(screen.getByText("+4.80%")).toBeTruthy();
    expect(screen.getByText("-1.20%")).toBeTruthy();
    expect(screen.getByText(/样本股票 600157 · 波段ID 12/)).toBeTruthy();
    expect(screen.getByText("已选中")).toBeTruthy();

    fireEvent.click(screen.getByText("已选中"));
    expect(onSelectCase).toHaveBeenCalledWith(301);
  });
});
