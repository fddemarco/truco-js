import { describe, expect, it } from "vitest";
import { LOCALES } from "$lib/i18n.svelte";
import { ruleHtml, ruleMarkdown, SECTIONS } from "./index";

describe("rules", () => {
  it("has every section in every locale, titled as in the index", () => {
    for (const section of SECTIONS) {
      for (const locale of LOCALES) {
        const markdown = ruleMarkdown(section.slug, locale);
        expect(markdown, `${locale}/${section.slug}`).toBeDefined();
        expect(markdown!.split("\n")[0]).toBe(`# ${section.title[locale]}`);
      }
    }
  });

  it("covers every chapter and annex of the reglamento in both locales", () => {
    for (const locale of LOCALES) {
      const all = SECTIONS.map((s) => ruleMarkdown(s.slug, locale)).join("\n");
      for (let chapter = 1; chapter <= 20; chapter++) {
        expect(all, `${locale} ch. ${chapter}`).toMatch(new RegExp(`^## ${chapter}\\. `, "m"));
      }
      for (const annex of ["A", "B", "C"]) {
        expect(all, `${locale} annex ${annex}`).toMatch(new RegExp(`^## Anexo ${annex}\\. `, "m"));
      }
    }
  });

  it("renders html without the title", () => {
    const html = ruleHtml("cantos", "en")!;
    expect(html).toContain("<table>");
    expect(html).not.toContain("<h1");
    expect(ruleHtml("missing", "es")).toBeUndefined();
  });
});
