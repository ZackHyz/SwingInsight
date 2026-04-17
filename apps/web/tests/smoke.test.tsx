// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import HomePage from "../src/app/page";

describe("smoke", () => {
  afterEach(() => cleanup());

  it("renders the terminal landing shell", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "SwingInsight 终端" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "总览" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "研究台" })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "主导航" }).className).toContain("app-shell__top-nav");
    expect(screen.queryByLabelText("Primary")).toBeNull();
    expect(screen.getByText("拐点编辑")).toBeTruthy();
  });
});
