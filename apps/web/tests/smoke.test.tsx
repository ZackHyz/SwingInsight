// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import HomePage from "../src/app/page";

describe("smoke", () => {
  afterEach(() => cleanup());

  it("renders the terminal landing shell", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "SwingInsight Terminal" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Overview" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Research" })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Main navigation" }).className).toContain("app-shell__top-nav");
    expect(screen.queryByLabelText("Primary")).toBeNull();
    expect(screen.getByText("Turning Point Editing")).toBeTruthy();
  });
});
