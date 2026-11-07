import { describe, expect, it } from "vitest";
import { cardName } from "./cards";

describe("cardName", () => {
  it("names cards in Spanish", () => {
    expect(cardName(1, "espada")).toBe("1 de espadas");
    expect(cardName(12, "copa")).toBe("12 de copas");
  });
});
