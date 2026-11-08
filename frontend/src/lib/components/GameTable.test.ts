import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GameAction, GameView } from "$lib/api/client";
import { avatarSrc, CHARACTERS, characterFor } from "$lib/avatar/avatar";
import { updateProfile } from "$lib/profile.svelte";
import GameTable from "./GameTable.svelte";

const action = (kind: GameAction["kind"], extra: Partial<GameAction> = {}): GameAction => ({
  kind,
  card: null,
  number: null,
  sena: null,
  ...extra,
});

function makeView(overrides: Partial<GameView> = {}): GameView {
  return {
    id: "g",
    mode: "strict",
    version: 1,
    server_ms: Date.now(),
    started: true,
    match_phase: "in_hand",
    seats: Array.from({ length: 6 }, (_, i) => ({
      seat: i,
      team: i % 2,
      number: 1,
      name: `P${i}`,
      character: CHARACTERS[i],
      kind: i === 0 ? "human" : "bot",
      joined: true,
      in_play: true,
      active: true,
      cards_left: 3,
      shown: [],
      played: [],
    })),
    team_names: ["Los Pumas", "Los Teros"],
    score: [3, 7],
    hand_number: 2,
    hand_kind: "redonda",
    dealer: 5,
    mano: 0,
    pie: 5,
    phase: "playing",
    to_act: 0,
    duel: null,
    rounds: [[]],
    results: [],
    pending: [],
    envido_calls: [],
    truco_level: 0,
    truco_accepted: 0,
    envido: null,
    declarations: {},
    can_deal: false,
    result: null,
    events: [{ seat: 1, kind: "truco", card: null, number: null, points: null, upheld: null }],
    senas: [],
    me: 0,
    my_cards: [
      { number: 1, suit: "espada" },
      { number: 4, suit: "oro" },
    ],
    actions: [
      action("jugar", { card: { number: 1, suit: "espada" } }),
      action("quiero"),
      action("no_quiero"),
    ],
    senas_seen: [],
    ...overrides,
  };
}

function setup(view: GameView, extra = {}) {
  const onAct = vi.fn();
  const onCut = vi.fn();
  const onSena = vi.fn();
  render(GameTable, { view, viewer: 0, onAct, onCut, onSena, ...extra });
  return { onAct, onCut, onSena };
}

afterEach(() => vi.useRealTimers());

describe("GameTable", () => {
  it("plays a card that is legal and disables the others", async () => {
    const { onAct } = setup(makeView());
    const ancho = screen.getByRole("button", { name: "1 de espadas" }) as HTMLButtonElement;
    const cuatro = screen.getByRole("button", { name: "4 de oros" }) as HTMLButtonElement;
    expect(cuatro.disabled).toBe(true);
    await fireEvent.click(ancho);
    expect(onAct).toHaveBeenCalledWith(action("jugar", { card: { number: 1, suit: "espada" } }));
  });

  it("answers with the canto buttons", async () => {
    const { onAct } = setup(makeView());
    await fireEvent.click(screen.getByRole("button", { name: "No quiero" }));
    expect(onAct).toHaveBeenCalledWith(action("no_quiero"));
  });

  it("declares a tanto from the number pad", async () => {
    const view = makeView({ actions: [action("declarar", { number: 31 }), action("son_buenas")] });
    const { onAct } = setup(view);
    await fireEvent.click(screen.getByRole("button", { name: "31" }));
    expect(onAct).toHaveBeenCalledWith(action("declarar", { number: 31 }));
    expect(screen.getByRole("button", { name: "Son buenas" })).toBeTruthy();
  });

  it("lets the cutter cut between manos, with the button or the space bar", async () => {
    const view = makeView({ can_deal: true, actions: [], to_act: null });
    const { onCut } = setup(view, { nextDeal: { cutter: 0, mine: true, endsAt: Date.now() } });
    expect(screen.getByTestId("mazo-deck").dataset.state).toBe("shuffling");
    await fireEvent.click(screen.getByRole("button", { name: /Cortar/ }));
    await fireEvent.keyDown(window, { code: "Space" });
    expect(onCut).toHaveBeenCalledTimes(2);
  });

  it("counts down to the next mano when someone else cuts", () => {
    const view = makeView({ can_deal: true, actions: [], to_act: null });
    setup(view, { nextDeal: { cutter: 4, mine: false, endsAt: Date.now() + 2500 } });
    expect(screen.getByTestId("next-deal").textContent).toMatch(/3 s.*P4/);
    expect(screen.queryByRole("button", { name: /Cortar/ })).toBeNull();
  });

  it("shows the score, the moves and the result", () => {
    setup(makeView({ result: { kind: "deportivo", winner: 1 }, score: [22, 30] }));
    expect(screen.getByTestId("score-1").textContent).toBe("30");
    // The log shows who by their avatar.
    const log = screen.getByTestId("events");
    expect(log.textContent).toContain("Truco");
    expect(within(log).getByRole("img", { name: "P1" })).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("Ganaron Los Teros");
  });

  it("sends a seña held on the keyboard in interactive mode", async () => {
    vi.useFakeTimers();
    const { onSena } = setup(makeView({ mode: "interactive" }));
    await fireEvent.keyDown(window, { code: "Digit8" });
    vi.advanceTimersByTime(700);
    await fireEvent.keyUp(window, { code: "Digit8" });
    expect(onSena).toHaveBeenCalledWith("sena_12", "nariz", 700);
  });

  it("ignores seña keys in strict mode", async () => {
    const { onSena } = setup(makeView());
    await fireEvent.keyDown(window, { code: "Digit1" });
    await fireEvent.keyUp(window, { code: "Digit1" });
    expect(onSena).not.toHaveBeenCalled();
  });

  it("only shows the seña of the player across in focus, and pans with the arrows", async () => {
    const now = Date.now();
    const sena = (seat: number) => ({
      seat,
      sena: "sena_02" as const,
      spot: "ojo_derecho" as const,
      target: null,
      start_ms: now - 100,
      duration_ms: 5000,
    });
    // The viewer (seat 0) sits on side 0; across, from left to right: 5, 4, 3.
    const onLook = vi.fn();
    setup(makeView({ mode: "interactive", server_ms: now, senas: [sena(3), sena(5)] }), {
      onLook,
    });
    const avatar = (seat: number) =>
      screen.getByTestId(`seat-${seat}`).querySelector("img[data-variant]")?.getAttribute("src");
    expect(onLook).toHaveBeenLastCalledWith(5); // straight across first
    expect(avatar(5)).toBe(avatarSrc(characterFor(5), "sena_02"));
    expect(avatar(3)).toBe(avatarSrc(characterFor(3))); // not looking at 3 yet

    await fireEvent.keyDown(window, { key: "ArrowRight", code: "ArrowRight" });
    await fireEvent.keyDown(window, { key: "ArrowRight", code: "ArrowRight" });
    expect(onLook).toHaveBeenLastCalledWith(3);
    expect(avatar(3)).toBe(avatarSrc(characterFor(3), "sena_02"));
    expect(avatar(5)).toBe(avatarSrc(characterFor(5)));
    // Seats on the viewer's own side are there, but out of focus: never a seña to read.
    expect(screen.getByTestId("badge-1").dataset.look).toBe("blur");
    expect(screen.getByTestId("badge-0").dataset.look).toBe("focus");
    expect(avatar(1)).toBe(avatarSrc(characterFor(1)));
  });

  it("keeps every played card on its owner's stack", () => {
    const seats = makeView().seats.map((s) =>
      s.seat === 4
        ? {
            ...s,
            played: [
              { number: 7, suit: "oro" },
              { number: 3, suit: "copa" },
            ],
          }
        : s,
    );
    setup(makeView({ seats }));
    const stack = screen.getByTestId("stack-4");
    expect([...stack.querySelectorAll("img")].map((i) => i.getAttribute("alt"))).toEqual([
      "7 de oros",
      "3 de copas",
    ]);
  });

  it("says a canto out loud and blocks moves while beats play", () => {
    setup(makeView(), {
      busy: true,
      beat: { id: 1, seat: 3, kind: "truco", ms: 1500, think: 850 },
    });
    // by the speaker and, as a loud canto, across the whole table
    expect(screen.getAllByText("¡Truco!")).toHaveLength(2);
    expect(screen.getByLabelText("pensando")).toBeTruthy(); // a bot thinks first
    expect(screen.getByTestId("prompt").textContent).toContain("Juega P3");
    expect(screen.queryByRole("button", { name: "Quiero" })).toBeNull();
    expect(screen.getByRole("button", { name: "1 de espadas" }).hasAttribute("disabled")).toBe(
      true,
    );
  });

  it("flies the card being played onto its stack", () => {
    const seats = makeView().seats.map((s) =>
      s.seat === 2 ? { ...s, played: [{ number: 12, suit: "basto" }] } : s,
    );
    setup(makeView({ seats }), {
      beat: {
        id: 2,
        seat: 2,
        kind: "jugar",
        card: { number: 12, suit: "basto" },
        ms: 700,
        think: 0,
      },
    });
    expect(screen.getByTestId("stack-2").querySelector(".fly")).not.toBeNull();
    expect(screen.getByTestId("stack-4").querySelector(".fly")).toBeNull();
  });

  it("tells the player what to do and how the mano stands", () => {
    setup(
      makeView({
        pending: [{ family: "truco", chanter: 1, in_turn: true, irregular: false }],
        truco_level: 1,
        results: [1],
        envido_calls: ["envido"],
      }),
    );
    const hint = screen.getByTestId("prompt");
    expect(hint.dataset.tone).toBe("answer");
    expect(hint.textContent).toContain("P1 cantó Truco");
    expect(screen.getByTestId("status-truco").textContent).toContain("Truco");
    expect(screen.getByTestId("status-envido").textContent).toContain("cantado");
    // answers come first and stand out
    expect(
      within(screen.getByRole("group", { name: "Responder" })).getByRole("button", {
        name: "Quiero",
      }),
    ).toBeTruthy();
  });

  it("sends the cards of a player who goes to the mazo onto it", () => {
    setup(makeView(), {
      busy: true,
      beat: { id: 3, seat: 4, kind: "me_voy_al_mazo", ms: 1500, think: 850 },
    });
    expect(screen.getAllByTestId("to-mazo")).toHaveLength(3);
    expect(screen.getAllByText("Me voy al mazo").length).toBeGreaterThan(0);
  });

  it("announces who won the ronda and lights up the winning card", () => {
    const seats = makeView().seats.map((s) =>
      s.seat === 5 ? { ...s, played: [{ number: 1, suit: "espada" }] } : s,
    );
    setup(makeView({ seats }), {
      busy: true,
      beat: { id: 4, seat: 5, kind: "ronda", number: 1, ms: 1600, think: 0 },
    });
    expect(screen.getByText("Ronda 1: gana P5")).toBeTruthy();
    expect(screen.getByTestId("stack-5").querySelector(".winner")).not.toBeNull();
  });

  it("conjugates for the viewer when they win the ronda", () => {
    setup(makeView(), {
      busy: true,
      beat: { id: 5, seat: 0, kind: "ronda", number: 2, ms: 1600, think: 0 },
    });
    expect(screen.getByText("Ronda 2: ganaste vos")).toBeTruthy();
  });
});

describe("GameTable, more", () => {
  it("highlights the card winning the ronda so far, silver for a parda", () => {
    const played = (seat: number, number: number, suit: string) => ({
      seat,
      card: { number, suit },
    });
    const withCards = (plays: ReturnType<typeof played>[]) =>
      makeView({
        rounds: [plays],
        seats: makeView().seats.map((s) => {
          const p = plays.find((x) => x.seat === s.seat);
          return p ? { ...s, played: [p.card] } : s;
        }),
      });
    setup(withCards([played(0, 4, "copa"), played(1, 7, "oro"), played(2, 3, "basto")]));
    expect(
      screen.getByTestId("stack-1").querySelector("[data-lead]")?.getAttribute("data-lead"),
    ).toBe("lead");
    expect(screen.getByTestId("stack-2").querySelector("[data-lead]")).toBeNull();
  });

  it("marks mano and pie, and the viewer's team", () => {
    setup(makeView({ mano: 0, pie: 5 }));
    expect(within(screen.getByTestId("badge-0")).getByTestId("role-mano")).toBeTruthy();
    expect(within(screen.getByTestId("badge-5")).getByTestId("role-pie")).toBeTruthy();
    expect(screen.getByText("Tu equipo")).toBeTruthy();
  });

  it("plays and sings from the keyboard", async () => {
    const { onAct } = setup(
      makeView({
        actions: [action("jugar", { card: { number: 4, suit: "oro" } }), action("truco")],
      }),
    );
    await fireEvent.keyDown(window, { code: "KeyS" }); // the second card in hand
    expect(onAct).toHaveBeenLastCalledWith(action("jugar", { card: { number: 4, suit: "oro" } }));
    await fireEvent.keyDown(window, { code: "KeyT" });
    expect(onAct).toHaveBeenLastCalledWith(action("truco"));
  });
});

describe("GameTable, keys and help", () => {
  afterEach(() => updateProfile({ keys: "mnemonic", customKeys: {} }));

  it("follows the key layout chosen in the settings", async () => {
    updateProfile({ keys: "rows" });
    const { onAct } = setup(makeView());
    await fireEvent.keyDown(window, { code: "KeyQ" });
    expect(onAct).toHaveBeenLastCalledWith(action("quiero"));
    await fireEvent.keyDown(window, { code: "Digit1" }); // first card, by rows
    expect(onAct).toHaveBeenLastCalledWith(
      action("jugar", { card: { number: 1, suit: "espada" } }),
    );
    expect(screen.getByRole("button", { name: "Quiero" }).getAttribute("aria-keyshortcuts")).toBe(
      "Q",
    );
  });

  it("opens how to play from the gear, with the señas by meaning", async () => {
    setup(makeView());
    await fireEvent.click(screen.getByRole("button", { name: "Cómo jugar y teclas" }));
    const senas = screen.getByTestId("howto-senas");
    expect(within(senas).getByText("Ancho de espadas")).toBeTruthy();
    expect(within(senas).getByText("Fruncir la nariz")).toBeTruthy();
    await fireEvent.click(screen.getByRole("tab", { name: "Teclas" }));
    expect(screen.getByRole("radio", { name: /Mnemotécnica/ }).getAttribute("aria-checked")).toBe(
      "true",
    );
  });
});
