/**
 * Move animations: every card played or canto said takes one beat on screen, so a burst of bot
 * moves reads like a real table. A bot first "thinks" (dots over its head), then acts: 1-2 s in
 * all. Pure helpers plus a small timed queue; the play page owns the queue and `GameTable`
 * draws the current beat.
 */
import type { CardModel, GameEvent, GameView } from "$lib/api/client";

/** How long the move itself (card flight, words) is on screen. */
export const ACT_MS = 650;
/** A human's own move: no thinking, just the move. */
export const HUMAN_MS = 700;
/** Announcements (ronda won, envido result, end of the mano, new deal) stay long enough to read. */
export const BANNER_MS = 1600;
/** A bot thinks this long before it acts, so each of its moves takes 1-2 s. */
export const THINK_MS: [number, number] = [450, 1350];

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
  /** The event it shows, for the move log. */
  event: GameEvent;
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

const same = (a: GameEvent, b: GameEvent) => JSON.stringify(a) === JSON.stringify(b);

/**
 * The events in `next` that `prev` didn't have. The server sends a sliding window of recent
 * events, so this finds the longest tail of `prev` that starts `next`.
 */
export function newEvents(prev: GameEvent[], next: GameEvent[]): GameEvent[] {
  for (let k = Math.min(prev.length, next.length); k > 0; k--) {
    const tail = prev.slice(prev.length - k);
    if (tail.every((e, i) => same(e, next[i]))) return next.slice(k);
  }
  return prev.length ? next : [];
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

/** One beat per animated event. `bots` are the seats played by bots: they think first. */
export function beats(events: GameEvent[], bots: Set<number> = new Set()): Beat[] {
  return events
    .filter((e) => ANIMATED.has(e.kind))
    .map((e) => {
      const id = ++lastId;
      const seat = e.seat ?? null;
      const banner = BANNERS.has(e.kind);
      const think = !banner && seat !== null && bots.has(seat) ? thinkFor(id) : 0;
      const ms = banner ? BANNER_MS : think ? think + ACT_MS : HUMAN_MS;
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
      };
    });
}

/**
 * The view as it looks once `done` beats have played: played cards land on their owner's
 * stack (and leave the viewer's hand), rondas are scored, players at the mazo are out, a new
 * deal clears the table, and the move log grows one move at a time.
 *
 * Only the first `settled` beats count for the log, rondas and the mazo; later ones (a bot
 * still thinking) only put their card down, which stays hidden until its animation starts.
 */
export function applyBeats(view: GameView, done: Beat[], settled = done.length): GameView {
  if (!done.length) return view;
  const seats = view.seats.map((s) => ({ ...s, played: [...s.played] }));
  let myCards = [...view.my_cards];
  let results = [...view.results];
  let rounds = view.rounds.map((r) => [...r]);
  if (!rounds.length) rounds = [[]];
  const events = [...view.events];
  function landCard(b: Beat) {
    if (b.seat === null || !b.card) return;
    const card = b.card;
    const seat = seats[b.seat];
    seat.played.push(card);
    rounds[rounds.length - 1].push({ seat: b.seat, card });
    seat.cards_left = Math.max(0, seat.cards_left - 1);
    if (b.seat === view.me) {
      myCards = myCards.filter((c) => !(c.number === card.number && c.suit === card.suit));
    }
  }
  for (const [i, b] of done.entries()) {
    if (i >= settled) {
      if (b.kind === "jugar") landCard(b);
      continue;
    }
    events.push(b.event);
    if (b.kind === "reparto") {
      seats.forEach((s) => (s.played = []));
      results = [];
      rounds = [[]];
    }
    if (b.kind === "ronda") {
      results.push(b.seat === null ? null : seats[b.seat].team);
      rounds.push([]);
    }
    if (b.seat !== null && LEAVE.has(b.kind)) {
      const team = seats[b.seat].team;
      for (const s of seats) {
        if (s.seat === b.seat || (b.kind === "nos_vamos_al_mazo" && s.team === team)) {
          s.active = false;
        }
      }
    }
    if (b.kind === "jugar") landCard(b);
  }
  return { ...view, seats, my_cards: myCards, results, rounds, events, actions: [] };
}

/**
 * The first view of a table has no previous one to diff against, so moves made before the
 * viewer arrived (bots playing the first ronda before the viewer's turn) would just appear.
 * `rewind` takes back the moves of the current mano since the viewer last acted (or since the
 * deal), so they can be replayed as beats: returns the rewound view and the events to replay.
 */
export function rewind(view: GameView): { view: GameView; replay: GameEvent[] } {
  const events = view.events;
  const deal = events.findLastIndex((e) => e.kind === "reparto");
  if (deal < 0 || view.match_phase !== "in_hand") return { view, replay: [] };
  const mine = events.findLastIndex((e, i) => i > deal && e.seat === view.me && e.seat !== null);
  const start = mine >= 0 ? mine + 1 : deal;
  const replay = events.slice(start);
  if (!replay.some((e) => ANIMATED.has(e.kind))) return { view, replay: [] };

  const seats = view.seats.map((s) => ({ ...s, played: [...s.played] }));
  let myCards = [...view.my_cards];
  let results = [...view.results];
  let rounds = (view.rounds ?? []).map((r) => [...r]);
  for (const e of [...replay].reverse()) {
    if (e.kind === "jugar" && e.seat !== null && e.seat !== undefined && e.card) {
      const seat = seats[e.seat];
      seat.played.pop();
      seat.cards_left += 1;
      rounds.at(-1)?.pop();
      if (e.seat === view.me) myCards = [...myCards, e.card];
    } else if (e.kind === "ronda") {
      results = results.slice(0, -1);
      if (rounds.length > 1) rounds = rounds.slice(0, -1);
    } else if (LEAVE.has(e.kind)) {
      // Whoever left in the replayed moves is back in until their move plays again.
      seats.forEach((s) => (s.active = s.active || s.in_play));
    }
  }
  return {
    view: { ...view, seats, my_cards: myCards, results, rounds, events: events.slice(0, start) },
    replay,
  };
}

/**
 * Plays beats one at a time. `onBeat(beat, done)` fires as each one starts, with the beats
 * already finished; `onIdle()` once the queue is empty again.
 */
export class BeatQueue {
  private queue: Beat[] = [];
  private done: Beat[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private onBeat: (beat: Beat, done: Beat[]) => void,
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
      this.done = [];
      this.onIdle();
      return;
    }
    this.onBeat(beat, [...this.done]);
    this.timer = setTimeout(() => {
      this.done.push(beat);
      this.next();
    }, beat.ms);
  }

  stop(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.queue = [];
    this.done = [];
  }
}
