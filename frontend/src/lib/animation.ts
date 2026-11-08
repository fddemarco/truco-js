/**
 * Move animations: every card played or canto said takes one beat on screen, so a burst of bot
 * moves reads like a real table. A bot first "thinks" (dots over its head), then acts: 1-2 s in
 * all. The server sends each move as a step with the table right after it (`StepView`), so a
 * beat only has to show that table: nothing is rebuilt here. Pure helpers plus a small timed
 * queue; the play page owns the queue and `GameTable` draws the current beat.
 */
import type { CardModel, GameEvent, GameView, StepView } from "$lib/api/client";

/** How long the move itself (card flight, words) is on screen. */
export const ACT_MS = 650;
/** A human's own move: no thinking, just the move. */
export const HUMAN_MS = 700;
/** Announcements (ronda won, envido result, end of the mano, new deal) stay long enough to read. */
export const BANNER_MS = 1600;
/** A new deal: the last mano's cards go back to the mazo (SWEEP_MS), then out to everyone. */
export const SWEEP_MS = 900;
const DEAL_MS = SWEEP_MS + 1500;
/** A bot thinks this long before it acts, so each of its moves takes 1-2 s. */
const THINK_MS: [number, number] = [450, 1350];

export interface Beat {
  /** Unique within a page, to restart CSS animations. */
  id: number;
  seat: number | null;
  kind: string;
  card?: CardModel | null;
  number?: number | null;
  points?: number[] | null;
  /** Total time on screen. */
  ms: number;
  /** The first part of it, before the move shows: the player thinking. */
  think: number;
  /** The event it shows. */
  event: GameEvent;
  /** The table once the move is made, as the server saw it (see `stepBeats`). */
  view: GameView;
}

/** Cantos said loud: bigger, louder text. */
export const LOUD = new Set([
  "truco",
  "retruco",
  "vale_cuatro",
  "envido",
  "real_envido",
  "falta_envido",
]);

/** Events shown as a beat. Others (señas, internal bookkeeping) just update the table. */
const ANIMATED = new Set([
  ...LOUD,
  "jugar",
  "quiero",
  "no_quiero",
  "son_buenas",
  "declarar",
  "me_voy_al_mazo",
  "nos_vamos_al_mazo",
  "tapar",
  "mostrar",
  "reclamar",
  "objetar",
  "pedir_perdon",
  "aceptar_perdon",
  "envido_resuelto",
  "ronda",
  "fin_mano",
  "reparto",
  "resultado",
]);

/** Moves that take a player out of the mano: their cards go to the mazo. */
export const LEAVE = new Set(["me_voy_al_mazo", "nos_vamos_al_mazo", "tapar"]);

/** Announcements, shown in the middle of the table rather than by a player. */
export const BANNERS = new Set(["ronda", "envido_resuelto", "fin_mano", "reparto", "resultado"]);

/** Bot thinking time: spread over THINK_MS, but fixed per beat so it can be tested. */
function thinkFor(id: number): number {
  const [lo, hi] = THINK_MS;
  return lo + ((id * 7919) % 10) * ((hi - lo) / 9);
}

/**
 * Whether `next` should replace `latest`. Responses can arrive out of order (a poll sent before
 * an action can answer after it), and an older view must never replace a newer one: its events
 * would not line up and every recent move would replay.
 */
export function isNewer(latest: GameView | null, next: GameView): boolean {
  if (latest === null || next.id !== latest.id || next.me !== latest.me) return true;
  return next.version > latest.version;
}

let lastId = 0;

/**
 * One beat per animated event of each step, showing that step's table. A move and what it sets
 * off (a ronda closing, the end of the mano) are one step, so its beats share the table.
 * Steps with nothing to animate (señas, bookkeeping) are folded into the next step's table.
 * `bots` are the seats played by bots: they think first.
 */
export function stepBeats(steps: StepView[], bots: Set<number> = new Set()): Beat[] {
  return steps.flatMap((step) => beats(step.events, step.view, bots));
}

function beats(events: GameEvent[], view: GameView, bots: Set<number>): Beat[] {
  return events
    .filter((e) => ANIMATED.has(e.kind))
    .map((e) => {
      const id = ++lastId;
      const seat = e.seat ?? null;
      const banner = BANNERS.has(e.kind);
      const think = !banner && seat !== null && bots.has(seat) ? thinkFor(id) : 0;
      const ms =
        e.kind === "reparto" ? DEAL_MS : banner ? BANNER_MS : think ? think + ACT_MS : HUMAN_MS;
      return {
        id,
        seat,
        kind: e.kind,
        card: e.card,
        number: e.number,
        points: e.points,
        ms,
        think,
        event: e,
        view,
      };
    });
}

/**
 * Plays beats one at a time. `onBeat(beat)` fires as each one starts; `onIdle()` once the queue
 * is empty again.
 */
export class BeatQueue {
  private queue: Beat[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private onBeat: (beat: Beat) => void,
    private onIdle: () => void,
  ) {}

  get busy(): boolean {
    return this.timer !== null;
  }

  push(more: Beat[]): void {
    this.queue.push(...more);
    if (!this.busy) this.next();
  }

  private next(): void {
    const beat = this.queue.shift();
    if (!beat) {
      this.timer = null;
      this.onIdle();
      return;
    }
    this.onBeat(beat);
    this.timer = setTimeout(() => this.next(), beat.ms);
  }

  stop(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.queue = [];
  }
}
