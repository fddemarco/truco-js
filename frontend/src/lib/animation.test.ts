import { afterEach, describe, expect, it, vi } from "vitest";
import type { GameEvent, GameView, StepView } from "$lib/api/client";
import { ACT_MS, BANNER_MS, BeatQueue, HUMAN_MS, isNewer, stepBeats, type Beat } from "./animation";

const ev = (kind: string, extra: Partial<GameEvent> = {}): GameEvent => ({
  seat: 1,
  kind,
  card: null,
  number: null,
  points: null,
  upheld: null,
  ...extra,
});

/** A step: the events of one move and the table right after it (only `version` tells them apart). */
let index = 0;
function step(events: GameEvent[], version = ++index): StepView {
  return { index, seat: events[0]?.seat ?? null, events, view: { version } as GameView };
}
const beats = (events: GameEvent[], bots?: Set<number>) => stepBeats([step(events)], bots);

describe("stepBeats", () => {
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

  it("shows each move on the table the server sent with it", () => {
    const deal = step([ev("reparto", { seat: null })], 10);
    const quiet = step([ev("sena", { seat: 2 })], 11); // nothing to animate
    const card = step([ev("jugar", { seat: 4 }), ev("ronda", { seat: 4, number: 1 })], 12);
    const out = stepBeats([deal, quiet, card]);
    expect(out.map((b) => [b.kind, b.view.version])).toEqual([
      ["reparto", 10], // the new mano, hands and all, from the deal on
      ["jugar", 12], // a card and the ronda it closes share their table
      ["ronda", 12],
    ]);
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

  it("drops what's left when stopped", () => {
    vi.useFakeTimers();
    const seen: string[] = [];
    const queue = new BeatQueue(
      (b: Beat) => seen.push(b.kind),
      () => {},
    );
    queue.push(beats([ev("truco"), ev("quiero")]));
    queue.stop();
    vi.advanceTimersByTime(HUMAN_MS * 2);
    expect(seen).toEqual(["truco"]);
    expect(queue.busy).toBe(false);
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
