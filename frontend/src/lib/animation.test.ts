import { afterEach, describe, expect, it, vi } from "vitest";
import type { GameEvent, GameView } from "$lib/api/client";
import {
  ACT_MS,
  applyBeats,
  BANNER_MS,
  BeatQueue,
  beats,
  isNewer,
  HUMAN_MS,
  newEvents,
  rewind,
  type Beat,
} from "./animation";

const ev = (kind: string, extra: Partial<GameEvent> = {}): GameEvent => ({
  seat: 1,
  kind,
  card: null,
  number: null,
  points: null,
  upheld: null,
  ...extra,
});

describe("newEvents", () => {
  it("returns only what was appended, also when the window slid", () => {
    const a = ev("truco", { seat: 1 });
    const b = ev("quiero", { seat: 2 });
    const c = ev("jugar", { seat: 3, card: { number: 4, suit: "oro" } });
    expect(newEvents([a, b], [a, b, c])).toEqual([c]);
    expect(newEvents([a, b], [b, c])).toEqual([c]); // the oldest event fell off the window
    expect(newEvents([a, b], [a, b])).toEqual([]);
  });

  it("animates nothing on the first view, and everything after a reset", () => {
    expect(newEvents([], [ev("truco")])).toEqual([]);
    const fresh = [ev("reparto", { seat: null, number: 9 })];
    expect(newEvents([ev("truco")], fresh)).toEqual(fresh);
  });
});

describe("beats", () => {
  it("makes a beat per card or canto and skips bookkeeping", () => {
    const out = beats([
      ev("jugar", { card: { number: 1, suit: "espada" } }),
      ev("declarar", { number: 27 }),
      ev("sena"),
      ev("interferencia"),
    ]);
    expect(out.map((b) => b.kind)).toEqual(["jugar", "declarar"]);
    expect(out[1].number).toBe(27);
    expect(out[0].id).not.toBe(out[1].id);
  });

  it("gives bots 1-2 s per move, thinking first; humans and announcements their own pace", () => {
    const bots = new Set([1, 2]);
    const many = beats(
      Array.from({ length: 20 }, (_, i) => ev("truco", { seat: 1 + (i % 2) })),
      bots,
    );
    for (const b of many) {
      expect(b.ms).toBeGreaterThanOrEqual(1000);
      expect(b.ms).toBeLessThanOrEqual(2000);
      expect(b.ms - b.think).toBe(ACT_MS);
    }
    expect(new Set(many.map((b) => b.ms)).size).toBeGreaterThan(1); // not robotic
    const [human, ronda] = beats([ev("quiero", { seat: 0 }), ev("ronda", { seat: 3 })], bots);
    expect(human).toMatchObject({ ms: HUMAN_MS, think: 0 });
    expect(ronda).toMatchObject({ ms: BANNER_MS, think: 0 });
  });
});

function view(): GameView {
  return {
    me: 0,
    seats: Array.from({ length: 6 }, (_, i) => ({ seat: i, cards_left: 3, played: [] })),
    my_cards: [
      { number: 1, suit: "espada" },
      { number: 4, suit: "oro" },
    ],
    actions: [{ kind: "quiero" }],
    results: [],
    rounds: [[]],
    events: [],
  } as unknown as GameView;
}

describe("applyBeats", () => {
  it("lands played cards on their owner's stack and out of the viewer's hand", () => {
    const [mine, theirs] = beats([
      ev("jugar", { seat: 0, card: { number: 4, suit: "oro" } }),
      ev("jugar", { seat: 3, card: { number: 7, suit: "copa" } }),
    ]);
    const out = applyBeats(view(), [mine, theirs]);
    expect(out.seats[0].played).toEqual([{ number: 4, suit: "oro" }]);
    expect(out.seats[3].played).toEqual([{ number: 7, suit: "copa" }]);
    expect(out.seats[3].cards_left).toBe(2);
    expect(out.my_cards).toEqual([{ number: 1, suit: "espada" }]);
    expect(out.actions).toEqual([]); // nothing to do while the table catches up
  });

  it("takes a player, or their whole team, out of the mano at the mazo", () => {
    const base = view();
    base.seats.forEach((s) => Object.assign(s, { team: s.seat % 2, active: true }));
    const [alone] = beats([ev("me_voy_al_mazo", { seat: 3 })]);
    expect(applyBeats(base, [alone]).seats.map((s) => s.active)).toEqual([
      true,
      true,
      true,
      false,
      true,
      true,
    ]);
    const [team] = beats([ev("nos_vamos_al_mazo", { seat: 2 })]);
    expect(applyBeats(base, [team]).seats.map((s) => s.active)).toEqual([
      false,
      true,
      false,
      true,
      false,
      true,
    ]);
  });

  it("scores rondas and logs moves only once they are settled", () => {
    const base = view();
    base.seats.forEach((s) => Object.assign(s, { team: s.seat % 2 }));
    const [card, ronda, next] = beats([
      ev("jugar", { seat: 3, card: { number: 1, suit: "espada" } }),
      ev("ronda", { seat: 3, number: 1 }),
      ev("jugar", { seat: 4, card: { number: 7, suit: "oro" } }),
    ]);
    const out = applyBeats(base, [card, ronda, next], 2);
    expect(out.results).toEqual([1]);
    // The ronda closed and the next one started with seat 4's card.
    expect(out.rounds).toEqual([
      [{ seat: 3, card: { number: 1, suit: "espada" } }],
      [{ seat: 4, card: { number: 7, suit: "oro" } }],
    ]);
    expect(out.events.map((e) => e.kind)).toEqual(["jugar", "ronda"]); // seat 4 still thinking
    expect(out.seats[4].played).toHaveLength(1); // its card is down, hidden by its animation
  });

  it("clears the table on a new deal", () => {
    const [card, deal] = beats([
      ev("jugar", { seat: 2, card: { number: 3, suit: "basto" } }),
      ev("reparto", { seat: null }),
    ]);
    expect(applyBeats(view(), [card, deal]).seats[2].played).toEqual([]);
  });
});

describe("BeatQueue", () => {
  afterEach(() => vi.useRealTimers());

  it("plays each beat for its own time, then goes idle", () => {
    vi.useFakeTimers();
    const seen: string[] = [];
    const onIdle = vi.fn();
    const queue = new BeatQueue((b: Beat) => seen.push(b.kind), onIdle);
    queue.push(beats([ev("truco"), ev("ronda")]));
    expect(seen).toEqual(["truco"]);
    vi.advanceTimersByTime(HUMAN_MS);
    expect(seen).toEqual(["truco", "ronda"]);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(BANNER_MS);
    expect(onIdle).toHaveBeenCalledOnce();
    expect(queue.busy).toBe(false);
  });

  it("passes the finished beats along so the table can catch up", () => {
    vi.useFakeTimers();
    const done: number[] = [];
    const queue = new BeatQueue(
      (_, d) => done.push(d.length),
      () => {},
    );
    queue.push(beats([ev("truco"), ev("quiero"), ev("no_quiero")]));
    vi.advanceTimersByTime(HUMAN_MS * 3);
    expect(done).toEqual([0, 1, 2]);
  });
});

describe("isNewer", () => {
  it("never lets an older response replace a newer one", () => {
    const v = (version: number, id = "g", me = 0) => ({ id, version, me }) as GameView;
    expect(isNewer(null, v(1))).toBe(true);
    expect(isNewer(v(5), v(6))).toBe(true);
    expect(isNewer(v(6), v(5))).toBe(false); // a slow poll answering after an action
    expect(isNewer(v(6), v(6))).toBe(false);
    expect(isNewer(v(6), v(1, "other"))).toBe(true);
    expect(isNewer(v(6), v(6, "g", 2))).toBe(true); // hot-seat: another seat's cards
  });
});

describe("rewind", () => {
  const card = (number: number, suit: string) => ({ number, suit });
  function entered(events: GameEvent[]): GameView {
    const v = view();
    v.match_phase = "in_hand";
    v.me = 0;
    v.events = events;
    v.seats.forEach((s) => Object.assign(s, { team: s.seat % 2, active: true, in_play: true }));
    return v;
  }

  it("takes back the first ronda played before the viewer arrived, to replay it", () => {
    const events = [
      ev("fin_mano", { seat: null }),
      ev("reparto", { seat: null, number: 2 }),
      ev("jugar", { seat: 4, card: card(7, "oro") }),
      ev("jugar", { seat: 5, card: card(1, "espada") }),
    ];
    const v = entered(events);
    v.seats[4] = { ...v.seats[4], played: [card(7, "oro")], cards_left: 2 };
    v.seats[5] = { ...v.seats[5], played: [card(1, "espada")], cards_left: 2 };
    const { view: back, replay } = rewind(v);
    expect(replay.map((e) => e.kind)).toEqual(["reparto", "jugar", "jugar"]);
    expect(back.seats[4].played).toEqual([]);
    expect(back.seats[5].cards_left).toBe(3);
    expect(back.events.map((e) => e.kind)).toEqual(["fin_mano"]);
    // Replaying the beats brings the table back to what the server sent.
    const again = applyBeats(back, beats(replay));
    expect(again.seats[4].played).toEqual(v.seats[4].played);
    expect(again.seats[5].played).toEqual(v.seats[5].played);
  });

  it("only replays what happened since the viewer's own last move", () => {
    const v = entered([
      ev("reparto", { seat: null }),
      ev("jugar", { seat: 0, card: card(4, "copa") }),
      ev("jugar", { seat: 1, card: card(5, "copa") }),
      ev("ronda", { seat: 1, number: 1 }),
      ev("me_voy_al_mazo", { seat: 2 }),
    ]);
    v.seats[0] = { ...v.seats[0], played: [card(4, "copa")], cards_left: 2 };
    v.seats[1] = { ...v.seats[1], played: [card(5, "copa")], cards_left: 2 };
    v.seats[2] = { ...v.seats[2], active: false };
    v.results = [1];
    v.my_cards = [card(1, "oro"), card(2, "oro")];
    const { view: back, replay } = rewind(v);
    expect(replay.map((e) => e.kind)).toEqual(["jugar", "ronda", "me_voy_al_mazo"]);
    expect(back.seats[0].played).toEqual([card(4, "copa")]); // the viewer's own card stays
    expect(back.seats[1].played).toEqual([]);
    expect(back.results).toEqual([]);
    expect(back.seats[2].active).toBe(true);
    expect(back.my_cards).toHaveLength(2);
  });

  it("replays nothing between manos or when nothing happened yet", () => {
    const between = entered([ev("reparto", { seat: null }), ev("fin_mano", { seat: null })]);
    between.match_phase = "dealing";
    expect(rewind(between).replay).toEqual([]);
    expect(rewind(entered([])).replay).toEqual([]);
  });
});
