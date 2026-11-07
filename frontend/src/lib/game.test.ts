import { describe, expect, it } from "vitest";
import {
  activeSenas,
  actionLabel,
  buttonActions,
  loadTokens,
  saveToken,
  seatPosition,
  senaForCode,
} from "./game";

describe("seatPosition", () => {
  it("puts the viewer at the bottom and play moves to their right", () => {
    expect(seatPosition(3, 3)).toBe("bottom");
    expect(seatPosition(4, 3)).toBe("bottom-right");
    expect(seatPosition(0, 3)).toBe("top"); // the facing seat, same number
    expect(seatPosition(2, 3)).toBe("bottom-left");
  });
});

describe("senaForCode", () => {
  it("maps keys to señas and Shift to the left side", () => {
    expect(senaForCode("Digit2", false)).toEqual({ sena: "sena_02", spot: "ojo_derecho" });
    expect(senaForCode("Digit8", false)).toEqual({ sena: "sena_08", spot: "muneca_derecha" });
    expect(senaForCode("Digit8", true)).toEqual({ sena: "sena_08", spot: "muneca_izquierda" });
    expect(senaForCode("Digit2", true)?.spot).toBe("ojo_derecho"); // only one spot
    expect(senaForCode("KeyA", false)).toBeNull();
  });
});

describe("activeSenas", () => {
  it("keeps only señas being shown now", () => {
    const senas = [
      { seat: 1, sena: "sena_01", spot: "cejas", start_ms: 1000, duration_ms: 500, target: null },
      { seat: 2, sena: "sena_12", spot: "nariz", start_ms: 0, duration_ms: 100, target: null },
    ] as const;
    const active = activeSenas([...senas], 1200);
    expect([...active.keys()]).toEqual([1]);
  });
});

describe("actions", () => {
  it("labels actions with game terms and filters the action bar", () => {
    expect(actionLabel({ kind: "declarar", number: 31, card: null, sena: null })).toBe("31");
    expect(
      actionLabel({ kind: "jugar", card: { number: 1, suit: "espada" }, number: null, sena: null }),
    ).toBe("1 de espadas");
    const actions = [
      { kind: "jugar", card: { number: 1, suit: "espada" }, number: null, sena: null },
      { kind: "truco", card: null, number: null, sena: null },
      { kind: "sena", card: null, number: null, sena: "sena_01" },
    ] as const;
    expect(buttonActions([...actions]).map((a) => a.kind)).toEqual(["truco"]);
  });
});

describe("tokens", () => {
  it("remembers each seat's token per game", () => {
    saveToken("g1", 0, "a");
    saveToken("g1", 2, "b");
    expect(loadTokens("g1")).toEqual({ 0: "a", 2: "b" });
    expect(loadTokens("other")).toEqual({});
  });
});
