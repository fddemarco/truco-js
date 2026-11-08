import { describe, expect, it } from "vitest";
import type { ActionKind, GameAction } from "$lib/api/client";
import {
  actionForKey,
  bindable,
  COMMANDS,
  keyHint,
  keyLabel,
  PRESET_BINDINGS,
  rebind,
  resolveBindings,
  senaForCode,
} from "./keys";

const act = (kind: ActionKind, extra: Partial<GameAction> = {}): GameAction => ({
  kind,
  card: null,
  number: null,
  sena: null,
  ...extra,
});
const hand = [
  { number: 1, suit: "espada" },
  { number: 4, suit: "oro" },
  { number: 7, suit: "copa" },
];
const qwerty = PRESET_BINDINGS.qwerty;

describe("presets", () => {
  it("bind every command to a different key", () => {
    const codes = COMMANDS.map((c) => qwerty[c]);
    expect(codes.every(Boolean)).toBe(true);
    expect(new Set(codes).size).toBe(codes.length);
  });
});

describe("actionForKey", () => {
  it("plays the card in that slot, only when it's legal", () => {
    const actions = [act("jugar", { card: hand[1] }), act("truco")];
    expect(actionForKey("KeyD", actions, hand, qwerty)).toEqual(actions[0]);
    expect(actionForKey("KeyS", actions, hand, qwerty)).toBeNull(); // not a legal card
    expect(actionForKey("KeyF", actions, hand.slice(0, 2), qwerty)).toBeNull(); // no third card
  });

  it("sings and answers with the bound keys, the next truco level on the truco key", () => {
    const actions = [act("quiero"), act("no_quiero"), act("retruco"), act("vale_cuatro")];
    expect(actionForKey("KeyE", actions, [], qwerty)?.kind).toBe("quiero");
    expect(actionForKey("KeyW", actions, [], qwerty)?.kind).toBe("no_quiero");
    expect(actionForKey("KeyR", actions, [], qwerty)?.kind).toBe("retruco");
    expect(actionForKey("KeyT", actions, [], qwerty)).toBeNull(); // envido isn't legal now
    expect(actionForKey("Digit1", actions, [], qwerty)).toBeNull(); // a seña key
  });
});

describe("señas", () => {
  it("are held on their own keys, never 08–11 (C.3)", () => {
    expect(senaForCode("Digit2", qwerty)).toEqual({ sena: "sena_02", spot: "ojo_derecho" });
    expect(senaForCode("Digit8", qwerty)).toEqual({ sena: "sena_12", spot: "nariz" });
    expect(senaForCode("Digit9", qwerty)).toBeNull();
  });
});

describe("custom bindings", () => {
  it("lay over the preset, and a rebound key leaves its old command unbound", () => {
    const custom = resolveBindings("custom", { quiero: "KeyJ" });
    expect(custom.quiero).toBe("KeyJ");
    expect(custom.no_quiero).toBe("KeyW");
    const swapped = rebind(custom, "truco", "KeyJ");
    expect(swapped.truco).toBe("KeyJ");
    expect(swapped.quiero).toBe("");
    expect(resolveBindings("qwerty")).toEqual(qwerty);
  });

  it("never share a key with the preset under them", () => {
    // Saved over another layout: the preset's own command on that key steps aside.
    const custom = resolveBindings("custom", { quiero: "KeyR" });
    expect(custom.quiero).toBe("KeyR");
    expect(custom.truco).toBe("");
  });

  it("refuse keys that belong to the browser or to typing", () => {
    expect(bindable("KeyK")).toBe(true);
    expect(bindable("Escape")).toBe(false);
    expect(bindable("Tab")).toBe(false);
    expect(bindable("F5")).toBe(false);
  });

  it("label buttons with their key", () => {
    expect(keyHint("falta_envido", qwerty)).toBe("B");
    expect(keyHint("vale_cuatro", qwerty)).toBe("R");
    expect(keyHint("declarar", qwerty)).toBeNull();
    expect(keyLabel("Space")).toBe("␣");
    expect(keyLabel("ArrowLeft")).toBe("←");
  });
});
