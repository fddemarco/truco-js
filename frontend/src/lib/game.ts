import type { ActionKind, GameAction, GameView, SenaView } from "$lib/api/client";
import { SPOTS, type BodySpot, type Sena } from "$lib/avatar/avatar";
import { cardName, type Suit } from "$lib/cards";

/** Cantos and answers are game terms: Spanish in every locale. */
export const ACTION_LABELS: Record<ActionKind, string> = {
  jugar: "Jugar",
  envido: "Envido",
  real_envido: "Real envido",
  falta_envido: "Falta envido",
  truco: "Truco",
  retruco: "Quiero retruco",
  vale_cuatro: "Quiero vale cuatro",
  quiero: "Quiero",
  no_quiero: "No quiero",
  me_voy_al_mazo: "Me voy al mazo",
  nos_vamos_al_mazo: "Nos vamos al mazo",
  sena: "Seña",
  declarar: "Declarar",
  son_buenas: "Son buenas",
  reclamar: "Reclamar",
  objetar: "Objetar",
  pedir_perdon: "Pedir perdón",
  aceptar_perdon: "Aceptar perdón",
  tapar: "Tapar",
  mostrar: "Mostrar cartas",
};

export type SeatPosition =
  "bottom" | "bottom-right" | "top-right" | "top" | "top-left" | "bottom-left";
const POSITIONS: SeatPosition[] = [
  "bottom",
  "bottom-right",
  "top-right",
  "top",
  "top-left",
  "bottom-left",
];

/** Where `seat` sits on screen for `viewer` (at the bottom). Play moves to the right (5.5). */
export function seatPosition(seat: number, viewer: number): SeatPosition {
  return POSITIONS[(seat - viewer + 6) % 6];
}

/** Hold a key to make a seña: 1–9, 0, - and = are señas 01–12; Shift picks the left side. */
const SENA_CODES: Record<string, Sena> = {
  Digit1: "sena_01",
  Digit2: "sena_02",
  Digit3: "sena_03",
  Digit4: "sena_04",
  Digit5: "sena_05",
  Digit6: "sena_06",
  Digit7: "sena_07",
  Digit8: "sena_08",
  Digit9: "sena_09",
  Digit0: "sena_10",
  Minus: "sena_11",
  Equal: "sena_12",
};

export function senaForCode(code: string, shift: boolean): { sena: Sena; spot: BodySpot } | null {
  const sena = SENA_CODES[code];
  if (!sena) return null;
  const spots = SPOTS[sena];
  return { sena, spot: shift && spots.length > 1 ? spots[1] : spots[0] };
}

/** The seña each seat is showing at `serverNow`. */
export function activeSenas(senas: SenaView[], serverNow: number): Map<number, SenaView> {
  const active = new Map<number, SenaView>();
  for (const s of senas) {
    if (s.start_ms <= serverNow && serverNow <= s.start_ms + s.duration_ms) active.set(s.seat, s);
  }
  return active;
}

export function actionLabel(action: GameAction): string {
  if (action.kind === "declarar") return String(action.number);
  if (action.kind === "jugar" && action.card) {
    return cardName(action.card.number, action.card.suit as Suit);
  }
  return ACTION_LABELS[action.kind];
}

/** Buttons for the action bar: everything except cards, señas and declarations. */
export function buttonActions(actions: GameAction[]): GameAction[] {
  return actions.filter((a) => !["jugar", "sena", "declarar"].includes(a.kind));
}

export function canPlay(view: GameView, number: number, suit: string): boolean {
  return view.actions.some(
    (a) => a.kind === "jugar" && a.card?.number === number && a.card?.suit === suit,
  );
}

// --- seat tokens, per browser -------------------------------------------------------------

const tokenKey = (gameId: string) => `game:${gameId}`;

export function loadTokens(gameId: string): Record<number, string> {
  try {
    return JSON.parse(localStorage.getItem(tokenKey(gameId)) ?? "{}");
  } catch {
    return {};
  }
}

export function saveToken(gameId: string, seat: number, token: string): void {
  try {
    localStorage.setItem(
      tokenKey(gameId),
      JSON.stringify({ ...loadTokens(gameId), [seat]: token }),
    );
  } catch {
    // Storage unavailable: the token lives only in this page.
  }
}
