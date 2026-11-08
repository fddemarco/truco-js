/**
 * Keyboard play, with configurable bindings. Keys are physical (`KeyboardEvent.code`), so they
 * sit in the same place on any layout. A preset, or a custom set laid over it (in the profile).
 * "qwerty" places each move by how often it comes up, for the left hand on the keyboard and the
 * right on the mouse: the cards rest under three fingers (S D F), the answers sit right above
 * them (E quiero, W no quiero), truco on R, the envido family down the index column (T G B),
 * son buenas on A. Moves that give the mano away (Q, Z) and the rare interactive ones (X C V,
 * Y H) are a reach away. Space cuts, señas are held on 1–8.
 */
import type { ActionKind, CardModel, GameAction } from "$lib/api/client";
import { SENA_NAMES, SENAS, SPOTS, type BodySpot, type Sena } from "$lib/avatar/avatar";
import { t, type MessageKey } from "$lib/i18n.svelte";

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

/** The commands as the key lists show them, by group (titles are i18n keys). */
export const KEY_GROUPS: { title: MessageKey; commands: Command[] }[] = [
  { title: "keys.group.cards", commands: ["card1", "card2", "card3"] },
  {
    title: "keys.group.cantos",
    commands: [
      "quiero",
      "no_quiero",
      "envido",
      "real_envido",
      "falta_envido",
      "truco",
      "son_buenas",
    ],
  },
  {
    title: "keys.group.other",
    commands: [
      "me_voy_al_mazo",
      "nos_vamos_al_mazo",
      "objetar",
      "perdon",
      "mostrar",
      "tapar",
      "reclamar",
    ],
  },
  { title: "keys.group.table", commands: ["cut", "look_left", "look_right"] },
  { title: "keys.group.senas", commands: SENAS },
];

/** What a command does, in the UI language (señas by their name). */
export function commandLabel(c: Command): string {
  return c.startsWith("sena_")
    ? SENA_NAMES[c as Sena]
    : t(`keys.cmd.${c as PlayCommand}` as MessageKey);
}

/** Command → key code ("" = unbound). */
export type Bindings = Record<Command, string>;

export const KEY_PRESETS = ["qwerty"] as const;
export type KeyPreset = (typeof KEY_PRESETS)[number];
export type KeyChoice = KeyPreset | "custom";

export const PRESET_BINDINGS: Record<KeyPreset, Bindings> = {
  qwerty: {
    card1: "KeyS",
    card2: "KeyD",
    card3: "KeyF",
    quiero: "KeyE",
    no_quiero: "KeyW",
    truco: "KeyR",
    envido: "KeyT",
    real_envido: "KeyG",
    falta_envido: "KeyB",
    son_buenas: "KeyA",
    me_voy_al_mazo: "KeyQ",
    nos_vamos_al_mazo: "KeyZ",
    objetar: "KeyX",
    reclamar: "KeyC",
    perdon: "KeyV",
    mostrar: "KeyY",
    tapar: "KeyH",
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
};

/** The preset under a custom set: what any command it doesn't rebind stays on. */
export const DEFAULT_PRESET: KeyPreset = "qwerty";

/**
 * The bindings in use: a preset, or the custom set laid over the default one. A default key
 * the custom set took for another command is left unbound, so two commands never share a key.
 */
export function resolveBindings(choice: KeyChoice, custom: Partial<Bindings> = {}): Bindings {
  if (choice !== "custom") return { ...PRESET_BINDINGS[choice] };
  const taken = new Set(Object.values(custom).filter(Boolean));
  const base = { ...PRESET_BINDINGS[DEFAULT_PRESET] };
  for (const c of COMMANDS) if (!(c in custom) && taken.has(base[c])) base[c] = "";
  return { ...base, ...custom };
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
