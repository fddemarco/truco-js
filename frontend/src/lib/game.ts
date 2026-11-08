import type { ActionKind, GameAction, GameView, SenaView } from "$lib/api/client";
import { cardName, trucoRank, type Suit } from "$lib/cards";
import type { MessageKey } from "$lib/i18n.svelte";

/** Cantos and answers are game terms: Spanish in every locale. */
/** The modality of a mano (§2). Game terms: Spanish in every locale. */
export const HAND_KINDS: Record<string, string> = { redonda: "Redonda", pica_pica: "Pica-pica" };

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

// --- seating ---------------------------------------------------------------------------------
// A rectangular table, three per side (1.2). Going around it, side 0 has seats 0-1-2 from left
// to right and side 1 continues with 3-4-5, so play (seat + 1, to the right, 5.5) moves around
// the table. Mirrors `app/truco/table.py`.

export const tableSide = (seat: number): number => Math.floor(seat / 3);

/** The seat directly across the table. */
export const across = (seat: number): number => 5 - seat;

/** The three seats on the other side, from the viewer's left to their right. */
export function seatsAcross(viewer: number): number[] {
  const first = 3 * tableSide(viewer);
  return [first, first + 1, first + 2].map(across);
}

/**
 * The next deal, once a mano is over. The server deals by itself at `deal_at` (its clock; the
 * offset turns it into this device's); the cutter, the player to the dealer's left (5.5), may
 * cut sooner. `mine`: the cutter is on this device, so it shows "Cortar".
 */
export function nextDeal(
  view: GameView,
  mySeats: number[],
  offset: number,
): { cutter: number; mine: boolean; endsAt: number } | null {
  if (view.deal_at == null || view.cutter == null || view.result) return null;
  return {
    cutter: view.cutter,
    mine: mySeats.includes(view.cutter),
    endsAt: view.deal_at - offset,
  };
}

/**
 * The card(s) winning the ronda so far (Anexo A). Several when the best rank ties: `tie` if
 * that tie is between teams (a parda so far), else only the first of them counts.
 */
export function leadingCards(
  ronda: { seat: number; card: { number: number; suit: string } }[],
  teamOf: (seat: number) => number,
): { seats: number[]; tie: boolean } {
  if (!ronda.length) return { seats: [], tie: false };
  const ranks = ronda.map((p) => trucoRank(p.card.number, p.card.suit));
  const best = Math.max(...ranks);
  const top = ronda.filter((_, i) => ranks[i] === best).map((p) => p.seat);
  const tie = new Set(top.map(teamOf)).size > 1;
  return { seats: tie ? top : top.slice(0, 1), tie };
}

/** Where each card of a hand of `n` sits, in card widths and degrees. Closed, cards overlap
 * 70 %; open (on hover), 70 % of each card shows, spread along an arc. */
export function fanLayout(n: number, open: boolean): { x: number; rotate: number; lift: number }[] {
  const step = open ? 0.7 : 0.3;
  const spread = open ? 7 : 3; // degrees between cards
  const mid = (n - 1) / 2;
  return Array.from({ length: n }, (_, i) => {
    const off = i - mid;
    return { x: i * step, rotate: off * spread, lift: open ? Math.abs(off) * 0.06 : 0 };
  });
}

/** Width of a fanned hand, in card widths. */
export function fanWidth(n: number, open: boolean): number {
  return n ? 1 + (n - 1) * (open ? 0.7 : 0.3) : 0;
}

/**
 * A score as fósforos: squares of five, enough for the target (a 30 partido: six, three for
 * malas and three for buenas, 1.3).
 */
export function tally(points: number, target = 30): number[] {
  const p = Math.max(0, Math.min(target, points));
  return Array.from({ length: Math.ceil(target / 5) }, (_, i) =>
    Math.max(0, Math.min(5, p - i * 5)),
  );
}

/** Team names to draw from (the backend draws from the same kind of list). */
const TEAM_NAMES = [
  "Los Pumas",
  "Las Vizcachas",
  "Los Teros",
  "Los Carpinchos",
  "Las Mulitas",
  "Los Chimangos",
  "Los Horneros",
  "Las Calandrias",
  "Los Yaguaretés",
  "Los Ñandúes",
];

/** Two different team names, avoiding `current` when possible. */
export function drawTeamNames(random = Math.random, current: string[] = []): [string, string] {
  const fresh = TEAM_NAMES.filter((n) => !current.includes(n));
  const pool = fresh.length >= 2 ? fresh : TEAM_NAMES;
  const a = pool[Math.floor(random() * pool.length)];
  const rest = pool.filter((n) => n !== a);
  return [a, rest[Math.floor(random() * rest.length)]];
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

// --- what is going on, in words -----------------------------------------------------------

const TRUCO_LEVELS = ["", "Truco", "Retruco", "Vale cuatro"];

/** The canto waiting for an answer, if any: its label (a game term) and who sang it. */
export function pendingCanto(view: GameView): { label: string; chanter: number } | null {
  const p = view.pending.at(-1);
  if (!p) return null;
  const label =
    p.family === "envido"
      ? (ACTION_LABELS[view.envido_calls.at(-1) as ActionKind] ?? "Envido")
      : (TRUCO_LEVELS[view.truco_level] ?? "Truco");
  return { label, chanter: p.chanter };
}

export type PromptTone = "go" | "answer" | "wait" | "done";

/** What the viewer should do now, as an i18n key with its values. */
export interface Prompt {
  tone: PromptTone;
  key: MessageKey;
  vars?: Record<string, string | number>;
}

export function prompt(view: GameView): Prompt {
  const name = (seat: number) => view.seats[seat].name;
  if (view.result) {
    return view.result.winner === null
      ? { tone: "done", key: "game.noWinner" }
      : { tone: "done", key: "game.won", vars: { team: view.team_names[view.result.winner] } };
  }
  if (!view.started) return { tone: "wait", key: "game.waiting" };
  const kinds = new Set(view.actions.map((a) => a.kind));
  // Between manos the next deal comes by itself (see `nextDeal`), but reclamos stay open.
  if (view.can_deal && !kinds.has("reclamar")) return { tone: "wait", key: "game.prompt.dealWait" };
  const canto = pendingCanto(view);
  // Interactive: a canto fuera de turno can be answered while play goes on (13.4).
  if (kinds.has("quiero") && canto) {
    return {
      tone: "answer",
      key: "game.prompt.answer",
      vars: { name: name(canto.chanter), canto: canto.label },
    };
  }
  const other = view.to_act !== null && view.to_act !== undefined && view.to_act !== view.me;
  switch (view.phase) {
    case "declaring":
      if (!other) return { tone: "answer", key: "game.prompt.declare" };
      break;
    case "answering":
      if (other && canto) {
        return {
          tone: "wait",
          key: "game.prompt.waitAnswer",
          vars: { name: name(view.to_act!), canto: canto.label },
        };
      }
      break;
    case "playing":
      if (kinds.has("jugar")) return { tone: "go", key: "game.prompt.play" };
      break;
  }
  if (other) return { tone: "wait", key: "game.prompt.wait", vars: { name: name(view.to_act!) } };
  if (view.to_act === view.me) return { tone: "wait", key: "game.prompt.yourTurnBlocked" };
  return kinds.size
    ? { tone: "go", key: "game.prompt.act" }
    : { tone: "wait", key: "game.prompt.idle" };
}

/** The state of the mano at a glance: rondas so far, and the envido and truco. */
export interface TableStatus {
  /** One entry per ronda of the current mano or duelo: the winning team, "parda", or null if
   * still being played. */
  rondas: (number | "parda" | null)[];
  envido: {
    label: string;
    state: "sung" | "accepted" | "rejected";
    points?: number;
    /** The winning tanto, as said at the table. */
    tanto?: number | null;
  } | null;
  truco: { label: string; state: "sung" | "accepted" } | null;
}

export function status(view: GameView): TableStatus {
  const rondas: TableStatus["rondas"] = [0, 1, 2].map((i) => {
    if (i < view.results.length) return view.results[i] ?? "parda";
    return null;
  });
  let envido: TableStatus["envido"] = null;
  const calls = view.envido?.calls ?? view.envido_calls;
  if (calls.length) {
    const label = calls.map((c) => ACTION_LABELS[c as ActionKind] ?? c).join(" + ");
    envido = view.envido
      ? {
          label,
          state: view.envido.accepted ? "accepted" : "rejected",
          points: view.envido.points,
          tanto:
            view.envido.winner_seat != null
              ? (view.envido.tantos[view.envido.winner_seat] ?? null)
              : null,
        }
      : { label, state: "sung" };
  }
  const truco: TableStatus["truco"] =
    view.truco_level > 0
      ? {
          label: TRUCO_LEVELS[view.truco_level],
          state: view.truco_accepted >= view.truco_level ? "accepted" : "sung",
        }
      : null;
  return { rondas, envido, truco };
}

// --- seat tokens, per browser -------------------------------------------------------------
// One entry per game: the seats this browser holds, the host token if it created the game,
// and when it was last used (old entries are pruned).

const GAME_PREFIX = "game:";
export const GAME_KEEP_MS = 7 * 24 * 3600 * 1000;

interface StoredGame {
  seats: Record<number, string>;
  host?: string;
  at: number;
}

function readGame(key: string): StoredGame | null {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return null;
    const data = JSON.parse(raw);
    if (data && typeof data === "object" && "seats" in data) return data as StoredGame;
    return { seats: data ?? {}, at: 0 }; // before the host token: just the seats
  } catch {
    return null;
  }
}

function writeGame(gameId: string, update: (game: StoredGame) => void): void {
  const game = readGame(GAME_PREFIX + gameId) ?? { seats: {}, at: 0 };
  update(game);
  game.at = Date.now();
  try {
    localStorage.setItem(GAME_PREFIX + gameId, JSON.stringify(game));
  } catch {
    // Storage unavailable: the token lives only in this page.
  }
}

export function loadTokens(gameId: string): Record<number, string> {
  return { ...(readGame(GAME_PREFIX + gameId)?.seats ?? {}) };
}

export function saveToken(gameId: string, seat: number, token: string): void {
  writeGame(gameId, (g) => (g.seats[seat] = token));
}

/** The seat was freed by the host: its token no longer works. */
export function forgetToken(gameId: string, seat: number): void {
  writeGame(gameId, (g) => delete g.seats[seat]);
}

export function loadHost(gameId: string): string | null {
  return readGame(GAME_PREFIX + gameId)?.host ?? null;
}

export function saveHost(gameId: string, token: string): void {
  writeGame(gameId, (g) => (g.host = token));
}

/** Mark a game as in use, so it isn't pruned. */
export function touchGame(gameId: string): void {
  if (readGame(GAME_PREFIX + gameId)) writeGame(gameId, () => {});
}

/** Forget the games not used for `keepMs`; how many were dropped. */
export function pruneGames(now = Date.now(), keepMs = GAME_KEEP_MS): number {
  let dropped = 0;
  try {
    const keys = Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i));
    for (const key of keys) {
      if (!key?.startsWith(GAME_PREFIX)) continue;
      const game = readGame(key);
      if (game && game.at === 0) {
        writeGame(key.slice(GAME_PREFIX.length), () => {}); // older format: its clock starts now
      } else if (!game || game.at < now - keepMs) {
        localStorage.removeItem(key);
        dropped++;
      }
    }
  } catch {
    // Storage unavailable: nothing to prune.
  }
  return dropped;
}
