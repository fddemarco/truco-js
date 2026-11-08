import { describe, expect, it } from "vitest";
import type { ActionKind, GameAction } from "$lib/api/client";
import {
  actionForKey,
  bindable,
  cardKeyHint,
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
const mnemonic = PRESET_BINDINGS.mnemonic;
const rows = PRESET_BINDINGS.rows;

describe("presets", () => {
  it("bind every command to a different key", () => {
    for (const preset of [mnemonic, rows]) {
      const codes = COMMANDS.map((c) => preset[c]);
      expect(codes.every(Boolean)).toBe(true);
      expect(new Set(codes).size).toBe(codes.length);
    }
  });
});

describe("actionForKey", () => {
  it("plays the card in that slot, only when it's legal", () => {
    const actions = [act("jugar", { card: hand[1] }), act("truco")];
    expect(actionForKey("KeyS", actions, hand, mnemonic)).toEqual(actions[0]);
    expect(actionForKey("Digit2", actions, hand, rows)).toEqual(actions[0]);
    expect(actionForKey("KeyA", actions, hand, mnemonic)).toBeNull();
    expect(actionForKey("KeyD", actions, hand.slice(0, 2), mnemonic)).toBeNull();
  });

  it("sings and answers with the bound keys, the next truco level on the truco key", () => {
    const actions = [act("quiero"), act("no_quiero"), act("retruco"), act("vale_cuatro")];
    expect(actionForKey("KeyQ", actions, [], mnemonic)?.kind).toBe("quiero");
    expect(actionForKey("KeyN", actions, [], mnemonic)?.kind).toBe("no_quiero");
    expect(actionForKey("KeyW", actions, [], rows)?.kind).toBe("no_quiero");
    expect(actionForKey("KeyT", actions, [], mnemonic)?.kind).toBe("retruco");
    expect(actionForKey("KeyE", actions, [], mnemonic)).toBeNull(); // envido isn't legal now
    expect(actionForKey("Digit1", actions, [], mnemonic)).toBeNull(); // a seña key
  });
});

describe("señas", () => {
  it("are held on their own keys, never 08–11 (C.3)", () => {
    expect(senaForCode("Digit2", mnemonic)).toEqual({ sena: "sena_02", spot: "ojo_derecho" });
    expect(senaForCode("Digit8", mnemonic)).toEqual({ sena: "sena_12", spot: "nariz" });
    expect(senaForCode("Digit9", mnemonic)).toBeNull();
    expect(senaForCode("Comma", rows)?.sena).toBe("sena_12");
  });
});

describe("custom bindings", () => {
  it("lay over the mnemonic preset, and a rebound key leaves its old command unbound", () => {
    const custom = resolveBindings("custom", { quiero: "KeyY" });
    expect(custom.quiero).toBe("KeyY");
    expect(custom.no_quiero).toBe("KeyN");
    const swapped = rebind(custom, "truco", "KeyY");
    expect(swapped.truco).toBe("KeyY");
    expect(swapped.quiero).toBe("");
    expect(resolveBindings("rows")).toEqual(rows);
  });

  it("refuse keys that belong to the browser or to typing", () => {
    expect(bindable("KeyK")).toBe(true);
    expect(bindable("Escape")).toBe(false);
    expect(bindable("Tab")).toBe(false);
    expect(bindable("F5")).toBe(false);
  });

  it("label buttons with their key", () => {
    expect(keyHint("falta_envido", mnemonic)).toBe("F");
    expect(keyHint("vale_cuatro", rows)).toBe("Y");
    expect(keyHint("declarar", mnemonic)).toBeNull();
    expect(cardKeyHint(2, rows)).toBe("3");
    expect(keyLabel("Space")).toBe("␣");
    expect(keyLabel("ArrowLeft")).toBe("←");
  });
});
