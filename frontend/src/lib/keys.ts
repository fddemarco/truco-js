/**
 * Keyboard play, with configurable bindings. Keys are physical (`KeyboardEvent.code`), so they
 * sit in the same place on any layout. Two presets and a custom set (kept in the profile):
 * - "mnemonic": letters by their initial (Q quiero, N no quiero, E envido, T truco...), cards
 *   on A S D, señas held on 1–8.
 * - "rows": one row per job: 1 2 3 the cards, the top row the cantos and answers, the home row
 *   everything else, the bottom row the señas.
 */
import type { ActionKind, CardModel, GameAction } from "$lib/api/client";
import { SENAS, SPOTS, type BodySpot, type Sena } from "$lib/avatar/avatar";

export const PLAY_COMMANDS = [
  "card1",
  "card2",
  "card3",
  "quiero",
  "no_quiero",
  "envido",
  "real_envido",
  "falta_envido",
  "truco",
  "son_buenas",
  "me_voy_al_mazo",
  "nos_vamos_al_mazo",
  "objetar",
  "perdon",
  "mostrar",
  "tapar",
  "reclamar",
  "cut",
  "look_left",
  "look_right",
] as const;
export type PlayCommand = (typeof PLAY_COMMANDS)[number];
/** A seña is held: the time the key is down is how long it lasts. */
export type Command = PlayCommand | Sena;
export const COMMANDS: Command[] = [...PLAY_COMMANDS, ...SENAS];

/** Command → key code ("" = unbound). */
export type Bindings = Record<Command, string>;

export const KEY_PRESETS = ["mnemonic", "rows"] as const;
export type KeyPreset = (typeof KEY_PRESETS)[number];
export type KeyChoice = KeyPreset | "custom";

export const PRESET_BINDINGS: Record<KeyPreset, Bindings> = {
  mnemonic: {
    card1: "KeyA",
    card2: "KeyS",
    card3: "KeyD",
    quiero: "KeyQ",
    no_quiero: "KeyN",
    envido: "KeyE",
    real_envido: "KeyR",
    falta_envido: "KeyF",
    truco: "KeyT",
    son_buenas: "KeyB",
    me_voy_al_mazo: "KeyM",
    nos_vamos_al_mazo: "KeyV",
    objetar: "KeyO",
    perdon: "KeyP",
    mostrar: "KeyW",
    tapar: "KeyX",
    reclamar: "KeyC",
    cut: "Space",
    look_left: "ArrowLeft",
    look_right: "ArrowRight",
    sena_01: "Digit1",
    sena_02: "Digit2",
    sena_03: "Digit3",
    sena_04: "Digit4",
    sena_05: "Digit5",
    sena_06: "Digit6",
    sena_07: "Digit7",
    sena_12: "Digit8",
  },
  rows: {
    card1: "Digit1",
    card2: "Digit2",
    card3: "Digit3",
    quiero: "KeyQ",
    no_quiero: "KeyW",
    envido: "KeyE",
    real_envido: "KeyR",
    falta_envido: "KeyT",
    truco: "KeyY",
    son_buenas: "KeyA",
    me_voy_al_mazo: "KeyS",
    nos_vamos_al_mazo: "KeyD",
    objetar: "KeyF",
    perdon: "KeyG",
    mostrar: "KeyH",
    tapar: "KeyJ",
    reclamar: "KeyK",
    cut: "Space",
    look_left: "ArrowLeft",
    look_right: "ArrowRight",
    sena_01: "KeyZ",
    sena_02: "KeyX",
    sena_03: "KeyC",
    sena_04: "KeyV",
    sena_05: "KeyB",
    sena_06: "KeyN",
    sena_07: "KeyM",
    sena_12: "Comma",
  },
};

/** The bindings in use: a preset, or the custom set laid over the mnemonic one. */
export function resolveBindings(choice: KeyChoice, custom: Partial<Bindings> = {}): Bindings {
  if (choice !== "custom") return { ...PRESET_BINDINGS[choice] };
  return { ...PRESET_BINDINGS.mnemonic, ...custom };
}

/** Bind `code` to `command`; any other command on that key is left unbound (no clashes). */
export function rebind(bindings: Bindings, command: Command, code: string): Bindings {
  const next = { ...bindings };
  for (const c of COMMANDS) if (next[c] === code) next[c] = "";
  next[command] = code;
  return next;
}

/** Keys that can't be bound: they belong to the browser or to typing. */
export function bindable(code: string): boolean {
  return !/^(Tab|Escape|Enter|NumpadEnter|Backspace|F\d+|Meta.*|Control.*|Alt.*|Shift.*|OS.*|ContextMenu|CapsLock)$/.test(
    code,
  );
}

const LABELS: Record<string, string> = {
  Space: "␣",
  ArrowLeft: "←",
  ArrowRight: "→",
  ArrowUp: "↑",
  ArrowDown: "↓",
  Comma: ",",
  Period: ".",
  Slash: "/",
  Semicolon: ";",
  Quote: "'",
  BracketLeft: "[",
  BracketRight: "]",
  Backslash: "\\",
  Minus: "-",
  Equal: "=",
  Backquote: "`",
};

/** A short label for a key code: "KeyA" → "A", "Digit1" → "1", "Space" → "␣". */
export function keyLabel(code: string): string {
  if (!code) return "";
  if (code in LABELS) return LABELS[code];
  if (code.startsWith("Key")) return code.slice(3);
  if (code.startsWith("Digit")) return code.slice(5);
  if (code.startsWith("Numpad")) return `Num ${code.slice(6)}`;
  return code;
}

/** The command an action answers to, if it has a key. */
function commandFor(kind: ActionKind): PlayCommand | null {
  switch (kind) {
    case "retruco":
    case "vale_cuatro":
      return "truco";
    case "pedir_perdon":
    case "aceptar_perdon":
      return "perdon";
    default:
      return (PLAY_COMMANDS as readonly string[]).includes(kind) ? (kind as PlayCommand) : null;
  }
}

/** The key label to show on a button for an action, if it has one. */
export function keyHint(kind: ActionKind, bindings: Bindings): string | null {
  const command = commandFor(kind);
  return command && bindings[command] ? keyLabel(bindings[command]) : null;
}

/** The key label for the i-th card in hand. */
export function cardKeyHint(i: number, bindings: Bindings): string | null {
  const command = (["card1", "card2", "card3"] as const)[i];
  return command && bindings[command] ? keyLabel(bindings[command]) : null;
}

/** The command bound to a key, if any. */
export function commandForCode(code: string, bindings: Bindings): Command | null {
  return COMMANDS.find((c) => bindings[c] === code) ?? null;
}

/**
 * The action a key press makes, if it's legal now. The truco key sings the next level
 * available (skipping a level is irregular, 12.3, so it never does).
 */
export function actionForKey(
  code: string,
  actions: GameAction[],
  myCards: CardModel[],
  bindings: Bindings,
): GameAction | null {
  const command = commandForCode(code, bindings);
  if (!command) return null;
  const slot = ["card1", "card2", "card3"].indexOf(command);
  if (slot >= 0) {
    const card = myCards[slot];
    if (!card) return null;
    return (
      actions.find(
        (a) => a.kind === "jugar" && a.card?.number === card.number && a.card.suit === card.suit,
      ) ?? null
    );
  }
  return actions.find((a) => commandFor(a.kind) === command) ?? null;
}

/** The seña a held key makes, if any. */
export function senaForCode(
  code: string,
  bindings: Bindings,
): { sena: Sena; spot: BodySpot } | null {
  const sena = SENAS.find((s) => bindings[s] === code);
  return sena ? { sena, spot: SPOTS[sena][0] } : null;
}
