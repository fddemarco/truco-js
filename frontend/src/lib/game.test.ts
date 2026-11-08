import { describe, expect, it } from "vitest";
import type { GameAction, GameView } from "$lib/api/client";
import {
  activeSenas,
  actionLabel,
  buttonActions,
  forgetToken,
  loadHost,
  loadTokens,
  pruneGames,
  saveHost,
  saveToken,
  GAME_KEEP_MS,
  across,
  pendingCanto,
  prompt,
  drawTeamNames,
  fanLayout,
  fanWidth,
  leadingCards,
  nextDeal,
  tally,
  seatsAcross,
  status,
} from "./game";

describe("seating", () => {
  it("puts three per side, with play moving around the table", () => {
    expect(seatsAcross(0)).toEqual([5, 4, 3]);
    expect(seatsAcross(4)).toEqual([2, 1, 0]);
    expect(across(2)).toBe(3); // the last of one side faces the first of the other
    expect(across(1)).toBe(4);
  });
});

describe("activeSenas", () => {
  it("keeps only señas being shown now", () => {
    const senas = [
      { seat: 1, sena: "sena_01", spot: "cejas", start_ms: 1000, duration_ms: 500, target: null },
      { seat: 2, sena: "sena_12", spot: "nariz", start_ms: 0, duration_ms: 100, target: null },
    ] as const;
    const active = activeSenas([...senas], 1200);
    expect([...active.keys()]).toEqual([1]);
  });
});

describe("actions", () => {
  it("labels actions with game terms and filters the action bar", () => {
    expect(actionLabel({ kind: "declarar", number: 31, card: null, sena: null })).toBe("31");
    expect(
      actionLabel({ kind: "jugar", card: { number: 1, suit: "espada" }, number: null, sena: null }),
    ).toBe("1 de espadas");
    const actions = [
      { kind: "jugar", card: { number: 1, suit: "espada" }, number: null, sena: null },
      { kind: "truco", card: null, number: null, sena: null },
      { kind: "sena", card: null, number: null, sena: "sena_01" },
    ] as const;
    expect(buttonActions([...actions]).map((a) => a.kind)).toEqual(["truco"]);
  });
});

describe("tokens", () => {
  it("remembers each seat's token per game", () => {
    saveToken("g1", 0, "a");
    saveToken("g1", 2, "b");
    expect(loadTokens("g1")).toEqual({ 0: "a", 2: "b" });
    expect(loadTokens("other")).toEqual({});
  });

  it("forgets a freed seat and keeps the host token beside the seats", () => {
    saveToken("g2", 1, "a");
    saveHost("g2", "h");
    forgetToken("g2", 1);
    expect(loadTokens("g2")).toEqual({});
    expect(loadHost("g2")).toBe("h");
  });

  it("reads tokens saved before the host token", () => {
    localStorage.setItem("game:old", JSON.stringify({ 3: "x" }));
    expect(loadTokens("old")).toEqual({ 3: "x" });
  });

  it("prunes games not used for a week", () => {
    localStorage.clear();
    saveToken("recent", 0, "a");
    saveToken("stale", 0, "b");
    localStorage.setItem("game:legacy", JSON.stringify({ 0: "c" }));
    localStorage.setItem("other", "kept");
    const stale = JSON.parse(localStorage.getItem("game:stale")!);
    localStorage.setItem("game:stale", JSON.stringify({ ...stale, at: 1 }));
    expect(pruneGames(Date.now(), GAME_KEEP_MS)).toBe(1);
    expect(loadTokens("stale")).toEqual({});
    expect(loadTokens("recent")).toEqual({ 0: "a" });
    expect(loadTokens("legacy")).toEqual({ 0: "c" }); // its clock starts now
    expect(localStorage.getItem("other")).toBe("kept");
    expect(pruneGames(Date.now() + GAME_KEEP_MS + 1)).toBe(2);
  });
});

const act = (kind: GameAction["kind"]): GameAction => ({
  kind,
  card: null,
  number: null,
  sena: null,
});

function table(over: Partial<GameView> = {}): GameView {
  return {
    started: true,
    phase: "playing",
    me: 0,
    to_act: 0,
    can_deal: false,
    result: null,
    seats: Array.from({ length: 6 }, (_, i) => ({ seat: i, name: `P${i}` })),
    team_names: ["Los Pumas", "Los Teros"],
    actions: [],
    pending: [],
    envido_calls: [],
    envido: null,
    truco_level: 0,
    truco_accepted: 0,
    results: [],
    ...over,
  } as unknown as GameView;
}

describe("nextDeal", () => {
  const between = (over: Partial<GameView> = {}) =>
    table({ can_deal: true, to_act: null, deal_at: 50_000, cutter: 4, ...over });

  it("turns the server's deal time into this device's clock", () => {
    expect(nextDeal(between(), [0], 1000)).toEqual({ cutter: 4, mine: false, endsAt: 49_000 });
  });

  it("lets the cutter on this device cut", () => {
    expect(nextDeal(between(), [0, 4], 0)?.mine).toBe(true);
  });

  it("has nothing to deal during a mano or after the partido", () => {
    expect(nextDeal(between({ deal_at: null, cutter: null }), [0], 0)).toBeNull();
    expect(nextDeal(between({ result: { kind: "deportivo", winner: 0 } }), [0], 0)).toBeNull();
  });
});

describe("leadingCards", () => {
  const team = (s: number) => s % 2;
  const play = (seat: number, number: number, suit: string) => ({ seat, card: { number, suit } });

  it("marks the best card of the ronda so far", () => {
    expect(leadingCards([], team)).toEqual({ seats: [], tie: false });
    const ronda = [play(0, 3, "copa"), play(1, 7, "oro"), play(2, 12, "basto")];
    expect(leadingCards(ronda, team)).toEqual({ seats: [1], tie: false });
  });

  it("marks both when the best cards of the two teams tie (parda so far)", () => {
    expect(leadingCards([play(0, 3, "copa"), play(1, 3, "oro")], team)).toEqual({
      seats: [0, 1],
      tie: true,
    });
    // Teammates tying is no parda: the first one counts.
    expect(leadingCards([play(0, 2, "copa"), play(2, 2, "oro")], team)).toEqual({
      seats: [0],
      tie: false,
    });
  });
});

describe("fanLayout", () => {
  it("overlaps the cards at rest and shows 70 % of each when open", () => {
    const closed = fanLayout(3, false);
    const open = fanLayout(3, true);
    expect(open[1].x - open[0].x).toBeCloseTo(0.7);
    expect(closed[1].x - closed[0].x).toBeCloseTo(0.3);
    expect(open[0].rotate).toBeLessThan(0);
    expect(open[1].rotate).toBe(0);
    expect(open[2].rotate).toBeGreaterThan(0);
    expect(fanWidth(3, true)).toBeCloseTo(2.4);
    expect(fanWidth(0, true)).toBe(0);
  });
});

describe("tally", () => {
  it("draws a score as squares of five fósforos", () => {
    expect(tally(0)).toEqual([0, 0, 0, 0, 0, 0]);
    expect(tally(13)).toEqual([5, 5, 3, 0, 0, 0]);
    expect(tally(30)).toEqual([5, 5, 5, 5, 5, 5]);
    expect(tally(34)).toEqual([5, 5, 5, 5, 5, 5]);
    expect(tally(12, 18)).toEqual([5, 5, 2, 0]); // a shorter partido: fewer squares
    expect(tally(20, 18)).toEqual([5, 5, 5, 3]);
  });
});

describe("team names", () => {
  it("draws two different names, fresh ones when possible", () => {
    const [a, b] = drawTeamNames(() => 0);
    expect(a).not.toBe(b);
    const again = drawTeamNames(() => 0, [a, b]);
    expect(again).not.toContain(a);
    expect(again).not.toContain(b);
  });
});

describe("prompt", () => {
  it("tells the viewer to play when a card can be played", () => {
    expect(prompt(table({ actions: [act("jugar"), act("truco")] }))).toMatchObject({
      tone: "go",
      key: "game.prompt.play",
    });
  });

  it("asks for an answer naming the canto and who sang it", () => {
    const view = table({
      actions: [act("quiero"), act("no_quiero"), act("retruco")],
      pending: [{ family: "truco", chanter: 3, in_turn: true, irregular: false }],
      truco_level: 2,
    });
    expect(prompt(view)).toEqual({
      tone: "answer",
      key: "game.prompt.answer",
      vars: { name: "P3", canto: "Retruco" },
    });
  });

  it("says who the table is waiting for, and on what", () => {
    expect(prompt(table({ to_act: 4 }))).toEqual({
      tone: "wait",
      key: "game.prompt.wait",
      vars: { name: "P4" },
    });
    const sung = table({
      phase: "answering",
      to_act: 1,
      pending: [{ family: "envido", chanter: 0, in_turn: true, irregular: false }],
      envido_calls: ["real_envido"],
    });
    expect(prompt(sung).vars).toEqual({ name: "P1", canto: "Real envido" });
  });

  it("waits on the player in turn, not on a canto fuera de turno", () => {
    const view = table({
      to_act: 4,
      pending: [{ family: "truco", chanter: 3, in_turn: false, irregular: false }],
      truco_level: 1,
    });
    expect(prompt(view)).toEqual({ tone: "wait", key: "game.prompt.wait", vars: { name: "P4" } });
  });

  it("asks for the tanto, the next deal, and announces the winner", () => {
    const declaring = table({ phase: "declaring", actions: [act("declarar")] });
    expect(prompt(declaring).key).toBe("game.prompt.declare");
    expect(prompt({ ...declaring, to_act: 2, actions: [] })).toEqual({
      tone: "wait",
      key: "game.prompt.wait",
      vars: { name: "P2" },
    });
    expect(prompt(table({ can_deal: true, to_act: null })).key).toBe("game.prompt.dealWait");
    expect(prompt(table({ result: { kind: "puntos", winner: 1 } }))).toEqual({
      tone: "done",
      key: "game.won",
      vars: { team: "Los Teros" },
    });
  });
});

describe("status", () => {
  it("lists the rondas so far and the envido and truco state", () => {
    const s = status(
      table({
        results: [1, null],
        envido: {
          calls: ["envido", "real_envido"],
          accepted: true,
          team: 0,
          points: 5,
          winner_seat: 2,
          tantos: { 0: 25, 2: 28 },
        },
        truco_level: 1,
        truco_accepted: 0,
      }),
    );
    expect(s.rondas).toEqual([1, "parda", null]);
    expect(s.envido).toEqual({
      label: "Envido + Real envido",
      state: "accepted",
      points: 5,
      tanto: 28,
    });
    expect(s.truco).toEqual({ label: "Truco", state: "sung" });
    expect(pendingCanto(table())).toBeNull();
  });
});
