import { describe, expect, it } from "vitest";
import { i18n, setLocale, t } from "./i18n.svelte";

describe("i18n", () => {
  it("defaults to Spanish and switches locale", () => {
    expect(i18n.locale).toBe("es");
    expect(t("nav.rules")).toBe("Reglamento");
    setLocale("en");
    expect(t("nav.rules")).toBe("Rules");
    expect(localStorage.getItem("locale")).toBe("en");
    setLocale("es");
  });
});
