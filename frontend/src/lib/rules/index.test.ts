import { describe, expect, it } from "vitest";
import { ruleHtml } from "./index";

describe("ruleHtml", () => {
  it("renders a section's markdown without its title", () => {
    const html = ruleHtml("cantos", "en")!;
    expect(html).toContain("<table>");
    expect(html).not.toContain("<h1");
  });

  it("returns undefined for an unknown section", () => {
    expect(ruleHtml("missing", "es")).toBeUndefined();
  });
});
