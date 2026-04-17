// @vitest-environment jsdom

import { describe, expect, it } from "vitest";

import { formatShanghaiDateTime } from "../src/lib/datetime";

describe("format shanghai date time", () => {
  it("formats utc timestamps in Asia/Shanghai", () => {
    expect(formatShanghaiDateTime("2026-04-17T00:00:00Z")).toBe("2026/4/17 08:00:00");
    expect(formatShanghaiDateTime("2026-04-16T22:26:14Z")).toBe("2026/4/17 06:26:14");
  });

  it("returns placeholder for empty values", () => {
    expect(formatShanghaiDateTime(null)).toBe("--");
    expect(formatShanghaiDateTime(undefined)).toBe("--");
    expect(formatShanghaiDateTime("")).toBe("--");
  });
});
