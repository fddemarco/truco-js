import { describe, expect, it } from "vitest";
import { formatDate } from "./format";

describe("formatDate", () => {
  it("renders missing dates as a dash", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });

  it("formats ISO timestamps", () => {
    expect(formatDate("2024-01-01T00:00:00Z")).not.toBe("—");
  });
});
