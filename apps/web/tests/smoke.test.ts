import { describe, expect, it } from "vitest";
import HomePage from "../src/app/page";

describe("smoke", () => {
  it("renders the workspace welcome copy", () => {
    const element = HomePage();
    expect(element).toBeTruthy();
  });
});
