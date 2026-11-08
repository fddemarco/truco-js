import { describe, expect, it } from "vitest";
import type { GameAction, GameView } from "$lib/api/client";
import {
  activeSenas,
  actionLabel,
  buttonActions,
  loadTokens,
  saveToken,
  across,
  besides,
  neighbours,
  pendingCanto,
  prompt,
  drawTeamNames,
  envidoBoard,
  fanLayout,
  fanWidth,
  leadingCards,
  nextDeal,
  tally,
  DEAL_WAIT_MS,
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

  it("knows who sits beside the viewer", () => {
    expect(neighbours(1)).toEqual({ left: 0, right: 2 });
    expect(neighbours(3)).toEqual({ left: null, right: 4 });
    expect(besides(4)).toEqual([3, 5]);
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
    table({
      can_deal: true,
      to_act: null,
      dealer: 2,
      mode: "strict",
      seats: Array.from({ length: 6 }, (_, i) => ({
        seat: i,
        name: `P${i}`,
        kind: i === 0 || i === 4 ? "human" : "bot",
      })),
      ...over,
    } as Partial<GameView>);

  it("lets the player to the dealer's left cut, on their device", () => {
    expect(nextDeal(between({ dealer: 1 }), [0])).toEqual({
      cutter: 0,
      mine: true,
      waitMs: DEAL_WAIT_MS.cut,
    });
  });

  it("waits for a human cutter elsewhere, and deals after a short pause for a bot", () => {
    expect(nextDeal(between({ dealer: 5 }), [0])).toMatchObject({ cutter: 4, mine: false });
    expect(nextDeal(between({ dealer: 5 }), [0])?.waitMs).toBe(DEAL_WAIT_MS.humanCutter);
    expect(nextDeal(between(), [0])).toMatchObject({ cutter: 1, waitMs: DEAL_WAIT_MS.strict });
    const interactive = between({ mode: "interactive" });
    expect(nextDeal(interactive, [0])?.waitMs).toBe(DEAL_WAIT_MS.interactive);
  });

  it("doesn't deal during a mano, after the partido, or for spectators", () => {
    expect(nextDeal(between({ can_deal: false }), [0])).toBeNull();
    expect(nextDeal(between({ result: { kind: "deportivo", winner: 0 } }), [0])).toBeNull();
    expect(nextDeal(between(), [])).toBeNull();
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

describe("envidoBoard", () => {
  it("tells what quiero and no quiero are worth while the canto waits", () => {
    const v = table({
      envido_calls: ["envido"],
      pending: [{ family: "envido", chanter: 3, in_turn: true, irregular: false }],
      envido_stakes: { quiero: [2, 2], no_quiero: 1, team: 1 },
    });
    expect(envidoBoard(v)).toMatchObject({ kind: "stakes", chanter: 3, quiero: [2], noQuiero: 1 });
    // a falta is worth what the winner lacks: one number per team
    const falta = { ...v, envido_stakes: { quiero: [27, 20], no_quiero: 1, team: 1 } };
    expect(envidoBoard(falta)).toMatchObject({ quiero: [27, 20] });
  });

  it("lists the numbers said in turn from mano, the first highest one best (11.4, 11.6)", () => {
    const v = table({
      phase: "declaring",
      mano: 4,
      to_act: 1,
      envido_calls: ["envido"],
      declarations: { 0: 28, 4: 28, 5: null },
    });
    expect(envidoBoard(v)).toEqual({
      kind: "declaring",
      label: "Envido",
      next: 1,
      said: [
        { seat: 4, number: 28, best: true },
        { seat: 5, number: null, best: false },
        { seat: 0, number: 28, best: false },
      ],
    });
  });

  it("announces who won only while the result beat is on screen", () => {
    const envido = { calls: ["envido"], accepted: true, team: 1, points: 2, winner_seat: 1 };
    const v = table({ mano: 0, envido: { ...envido, tantos: { 0: 25, 1: 30 } } });
    expect(envidoBoard(v)).toBeNull();
    expect(envidoBoard(v, true)).toMatchObject({ kind: "result", winner: 1, points: 2 });
    expect(envidoBoard(v, true)?.said.find((s) => s.best)?.seat).toBe(1);
  });
});
