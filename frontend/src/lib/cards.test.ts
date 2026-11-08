import { describe, expect, it } from "vitest";
import { cardName, trucoRank } from "./cards";

describe("cardName", () => {
  it("names cards in Spanish", () => {
    expect(cardName(1, "espada")).toBe("1 de espadas");
    expect(cardName(12, "copa")).toBe("12 de copas");
  });
});

describe("trucoRank", () => {
  it("follows the truco hierarchy (Anexo A)", () => {
    expect(trucoRank(1, "espada")).toBe(14);
    expect(trucoRank(7, "oro")).toBeGreaterThan(trucoRank(3, "copa"));
    expect(trucoRank(1, "copa")).toBe(trucoRank(1, "oro"));
    expect(trucoRank(7, "copa")).toBeLessThan(trucoRank(10, "basto"));
    expect(trucoRank(4, "espada")).toBe(1);
  });
});
