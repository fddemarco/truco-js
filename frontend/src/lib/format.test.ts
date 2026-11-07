import { describe, expect, it } from "vitest";
import { formatCell, formatDuration } from "./format";

describe("formatDuration", () => {
  it("formats seconds, minutes and hours", () => {
    const start = "2024-01-01T00:00:00Z";
    expect(formatDuration(start, "2024-01-01T00:00:01.5Z")).toBe("1.5s");
    expect(formatDuration(start, "2024-01-01T00:02:05Z")).toBe("2m 5s");
    expect(formatDuration(start, "2024-01-01T03:10:00Z")).toBe("3h 10m");
  });

  it("handles invalid input", () => {
    expect(formatDuration("nope")).toBe("—");
  });
});

describe("formatCell", () => {
  it("renders nulls and objects", () => {
    expect(formatCell(null)).toBe("∅");
    expect(formatCell({ a: 1 })).toBe('{"a":1}');
    expect(formatCell(3.5)).toBe("3.5");
  });
});
