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
    seats: Array.from({ length: 6 }, (_, i) => ({
      seat: i,
      team: i % 2,
      number: 1,
      name: `P${i}`,
      character: CHARACTERS[i],
      kind: i === 0 ? "human" : "bot",
      joined: true,
      online: true,
      in_play: true,
      active: true,
      cards_left: 3,
      shown: [],
      played: [],
    })),
    team_names: ["Los Pumas", "Los Teros"],
    score: [3, 7],
    target: 30,
    malas_max: 15,
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
    deal_at: null,
    cutter: null,
    pies: [null, null],
    stats: [],
    can_deal: false,
    result: null,
    events: [
      {
        seat: 1,
        kind: "truco",
        card: null,
        number: null,
        points: null,
        upheld: null,
        stakes: null,
        tantos: null,
        hand_kind: null,
      },
    ],
    senas: [],
    me: 0,
    my_tanto: null,
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
    step: 0,
    steps: [],
    base: null,
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

  it("declares the real tanto in one click, other numbers behind a toggle", async () => {
    const declarations = [27, 31].map((n) => action("declarar", { number: n }));
    const view = makeView({ my_tanto: 27, actions: [...declarations, action("son_buenas")] });
    const { onAct } = setup(view);
    expect(screen.getByText("Tu tanto: 27")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Son buenas" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "31" })).toBeNull();
    await fireEvent.click(screen.getByRole("button", { name: "Otro número" }));
    await fireEvent.click(screen.getByRole("button", { name: "31" }));
    expect(onAct).toHaveBeenCalledWith(action("declarar", { number: 31 }));
    await fireEvent.click(screen.getByRole("button", { name: "Declarar 27" }));
    expect(onAct).toHaveBeenLastCalledWith(action("declarar", { number: 27 }));
  });

  it("shows every number when the tanto is unknown", async () => {
    const view = makeView({ actions: [action("declarar", { number: 31 })] });
    const { onAct } = setup(view);
    await fireEvent.click(screen.getByRole("button", { name: "31" }));
    expect(onAct).toHaveBeenCalledWith(action("declarar", { number: 31 }));
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

  it("shows the score, the result and, when asked for, the moves", async () => {
    setup(makeView({ result: { kind: "deportivo", winner: 1 }, score: [22, 30] }));
    expect(screen.getByTestId("score-1").textContent).toBe("30");
    // The log shows only while hovered (no click); it shows who by their avatar.
    expect(screen.queryByTestId("events")).toBeNull();
    await fireEvent.mouseEnter(screen.getByTestId("moves"));
    const log = screen.getByTestId("events");
    expect(log.textContent).toContain("Truco");
    expect(within(log).getByRole("img", { name: "P1" })).toBeTruthy();
    await fireEvent.mouseLeave(screen.getByTestId("moves"));
    expect(screen.queryByTestId("events")).toBeNull();
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
    // Everyone but the player in focus and the viewer is dimmed alike, on either side.
    expect(screen.getByTestId("badge-1").dataset.look).toBe("dim");
    expect(screen.getByTestId("badge-5").dataset.look).toBe("dim");
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

  it("stacks cards whose position plus number would collide (3 then 2 of a suit)", () => {
    // The crash of 2026-11-08: keys built as i + number + suit made both "3basto".
    const seats = makeView().seats.map((s) =>
      s.seat === 4
        ? {
            ...s,
            played: [
              { number: 3, suit: "basto" },
              { number: 2, suit: "basto" },
            ],
          }
        : s,
    );
    setup(makeView({ seats }));
    const stack = screen.getByTestId("stack-4");
    expect(stack.querySelectorAll("img")).toHaveLength(2);
  });

  it("shows a bot thinking before its move, and nothing of the move yet", () => {
    setup(makeView(), {
      busy: true,
      thinking: true,
      beat: { id: 7, seat: 3, kind: "truco", ms: 1500, think: 850 },
    });
    expect(screen.getByLabelText("pensando")).toBeTruthy();
    expect(screen.queryByText("¡Truco!")).toBeNull();
    expect(screen.getByTestId("prompt").textContent).toContain("Juega P3");
  });

  it("says a canto out loud and blocks moves while beats play", () => {
    setup(makeView(), {
      busy: true,
      beat: { id: 1, seat: 3, kind: "truco", ms: 1500, think: 850 },
    });
    // by the speaker only: no banner across the table
    expect(screen.getAllByText("¡Truco!")).toHaveLength(1);
    expect(screen.queryByLabelText("pensando")).toBeNull(); // done thinking
    expect(screen.getByTestId("prompt").textContent).toContain("Juega P3");
    expect(screen.queryByRole("button", { name: "Quiero" })).toBeNull();
    expect(screen.getByRole("button", { name: "1 de espadas" }).hasAttribute("disabled")).toBe(
      true,
    );
  });

  it("sweeps the last mano's cards back to the mazo as a new mano is dealt", () => {
    setup(makeView(), {
      busy: true,
      swept: [2, 4],
      beat: { id: 8, seat: null, kind: "reparto", number: 2, ms: 2400, think: 0 },
    });
    expect(screen.getAllByTestId("sweep")).toHaveLength(2);
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
    // The scoreboard marks how the truco and the envido stand, and the rondas won.
    expect(screen.getByTestId("marker-truco").dataset.state).toBe("sung");
    expect(screen.getByTestId("marker-envido").dataset.state).toBe("sung");
    const teros = screen.getByRole("group", { name: "Los Teros" });
    expect(teros.querySelectorAll('[data-ronda="won"]')).toHaveLength(1);
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

  it("lights up the card that won the ronda, with no banner", () => {
    const seats = makeView().seats.map((s) =>
      s.seat === 5 ? { ...s, played: [{ number: 1, suit: "espada" }] } : s,
    );
    setup(makeView({ seats }), {
      busy: true,
      beat: { id: 4, seat: 5, kind: "ronda", number: 1, ms: 1600, think: 0 },
    });
    expect(screen.queryByText("Ronda 1: gana P5")).toBeNull();
    expect(screen.getByTestId("stack-5").querySelector(".winner")).not.toBeNull();
  });

  it("logs rondas, envidos and the end of a mano in their own style", async () => {
    const ev = (kind: string, extra = {}) => ({
      seat: null,
      kind,
      card: null,
      number: null,
      points: null,
      upheld: null,
      stakes: null,
      tantos: null,
      hand_kind: null,
      ...extra,
    });
    setup(
      makeView({
        events: [
          ev("truco", { seat: 1 }),
          ev("ronda", { seat: 0, number: 2 }),
          ev("envido_resuelto", { seat: 3, points: [0, 3] }),
          ev("fin_mano", { points: [1, 3] }),
        ],
      }),
    );
    await fireEvent.mouseEnter(screen.getByTestId("moves"));
    const log = screen.getByTestId("events");
    const row = (kind: string) => log.querySelector(`[data-kind="${kind}"]`)!;
    // the viewer gets their own conjugation, in their team's colour
    expect(row("ronda").textContent).toContain("Ronda 2: ganaste vos");
    expect(row("ronda").className).toContain("indigo");
    expect(row("envido_resuelto").textContent).toContain("+3");
    expect(row("fin_mano").textContent).toMatch(/Fin de la mano.*\+1.*\+3/);
    expect(row("truco").textContent).toContain("¡Truco!");
    // newest first
    expect(log.firstElementChild?.getAttribute("data-kind")).toBe("fin_mano");
  });
});

describe("GameTable, envido in the log", () => {
  const ev = (kind: string, extra = {}) => ({
    seat: null,
    kind,
    card: null,
    number: null,
    points: null,
    upheld: null,
    stakes: null,
    tantos: null,
    hand_kind: null,
    ...extra,
  });

  it("says what an envido is worth, and everyone's envido once it is played", async () => {
    setup(
      makeView({
        me: null, // a spectator sees it too
        events: [
          ev("falta_envido", { seat: 1, stakes: [27, 20, 1] }),
          ev("quiero", { seat: 2 }),
          ev("envido_resuelto", {
            seat: 3,
            number: 31,
            points: [0, 27],
            tantos: [25, 7, null, 31, 28, 20],
          }),
        ],
      }),
    );
    await fireEvent.mouseEnter(screen.getByTestId("moves"));
    const log = screen.getByTestId("events");
    const stakes = (within(log).getByTestId("stakes").textContent ?? "").replace(/\s+/g, " ");
    expect(stakes).toMatch(/Quiero.*\+27.*\+20/); // a falta: one value per team
    expect(stakes).toMatch(/No quiero \+1/);
    const tantos = within(log).getByTestId("envido-tantos");
    expect(tantos.querySelector('[data-seat="3"]')?.textContent).toMatch(/P3\s*31/);
    expect(tantos.querySelector('[data-seat="2"]')?.textContent).toMatch(/Son buenas/);
    expect(log.querySelector('[data-kind="envido_resuelto"]')?.textContent).toContain("+27");
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

  it("marks mano and a pie per team, the viewer's lighter, and the viewer's team", () => {
    setup(makeView({ mano: 0, pie: 5, pies: [4, 5] }));
    expect(within(screen.getByTestId("badge-0")).getByTestId("role-mano")).toBeTruthy();
    const pie = (seat: number) =>
      within(screen.getByTestId(`badge-${seat}`)).getByTestId("role-pie");
    expect(pie(4).dataset.own).toBe("true"); // the viewer (seat 0) is on team 0
    expect(pie(5).dataset.own).toBe("false");
    expect(screen.getByText("Tu equipo")).toBeTruthy();
  });

  it("plays and sings from the keyboard", async () => {
    const { onAct } = setup(
      makeView({
        actions: [action("jugar", { card: { number: 4, suit: "oro" } }), action("truco")],
      }),
    );
    await fireEvent.keyDown(window, { code: "KeyD" }); // the second card in hand
    expect(onAct).toHaveBeenLastCalledWith(action("jugar", { card: { number: 4, suit: "oro" } }));
    await fireEvent.keyDown(window, { code: "KeyR" });
    expect(onAct).toHaveBeenLastCalledWith(action("truco"));
  });
});

describe("GameTable, keys and help", () => {
  afterEach(() => updateProfile({ keys: "qwerty", customKeys: {} }));

  it("follows the custom keys chosen in the settings", async () => {
    updateProfile({ keys: "custom", customKeys: { quiero: "KeyJ", card1: "KeyK" } });
    const { onAct } = setup(makeView());
    await fireEvent.keyDown(window, { code: "KeyJ" });
    expect(onAct).toHaveBeenLastCalledWith(action("quiero"));
    await fireEvent.keyDown(window, { code: "KeyK" }); // the first card
    expect(onAct).toHaveBeenLastCalledWith(
      action("jugar", { card: { number: 1, suit: "espada" } }),
    );
    expect(screen.getByRole("button", { name: "Quiero" }).getAttribute("aria-keyshortcuts")).toBe(
      "J",
    );
  });

  it("opens how to play from the menu, with the señas by meaning", async () => {
    setup(makeView());
    await fireEvent.click(screen.getByRole("button", { name: "Cómo jugar" }));
    const senas = screen.getByTestId("howto-senas");
    expect(within(senas).getByText("Ancho de espadas")).toBeTruthy();
    expect(within(senas).getByText("Fruncir la nariz")).toBeTruthy();
    await fireEvent.click(screen.getByRole("tab", { name: "Teclas" }));
    expect(screen.getByRole("radio", { name: /Cómoda/ }).getAttribute("aria-checked")).toBe("true");
  });

  it("fills the window; Escape steps out and the corner button goes back", async () => {
    setup(makeView());
    const scene = screen.getByTestId("scene");
    expect(scene.dataset.immersive).toBe("true");
    await fireEvent.keyDown(window, { code: "Escape" });
    expect(scene.dataset.immersive).toBe("false");
    // Leaving says how to come back.
    expect(screen.getByTestId("fullscreen-hint").textContent).toContain(
      "volver a pantalla completa",
    );
    const button = screen.getByRole("button", { name: "Pantalla completa" });
    expect(button.getAttribute("aria-keyshortcuts")).toBe("F11");
    await fireEvent.click(button);
    expect(scene.dataset.immersive).toBe("true");
    expect(screen.getByTestId("fullscreen-hint").textContent).toContain(
      "salir de pantalla completa",
    );
  });

  it("toggles full screen with F11, like the button", async () => {
    setup(makeView());
    const scene = screen.getByTestId("scene");
    await fireEvent.keyDown(window, { code: "F11" });
    expect(scene.dataset.immersive).toBe("false");
    await fireEvent.keyDown(window, { code: "F11" });
    expect(scene.dataset.immersive).toBe("true");
  });

  it("shows the keys in use while Tab is held", async () => {
    updateProfile({ keys: "custom", customKeys: { quiero: "KeyJ" } });
    setup(makeView());
    expect(screen.queryByTestId("keymap")).toBeNull();
    await fireEvent.keyDown(window, { code: "Tab" });
    const map = screen.getByTestId("keymap");
    const row = within(map).getByText("Quiero").closest("li")!;
    expect(row.textContent).toContain("J");
    expect(within(map).queryByText(/Señas/)).toBeNull(); // strict: no señas keys
    await fireEvent.keyUp(window, { code: "Tab" });
    expect(screen.queryByTestId("keymap")).toBeNull();
  });

  it("opens the settings over the table, without bots", async () => {
    setup(makeView());
    await fireEvent.click(screen.getByRole("button", { name: "Ajustes" }));
    const dialog = screen.getByRole("dialog", { name: "Ajustes" });
    expect(within(dialog).getByRole("tab", { name: "Sonido" }).getAttribute("aria-selected")).toBe(
      "true",
    );
    expect(within(dialog).queryByRole("tab", { name: "Bots" })).toBeNull();
    expect(screen.getByTestId("scene")).toBeTruthy(); // the game is still there
    await fireEvent.keyDown(window, { code: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Ajustes" })).toBeNull();
  });

  it("says nothing when it is the viewer's turn to play: the cards light up instead", () => {
    setup(makeView({ phase: "playing" }));
    expect(screen.queryByTestId("prompt")).toBeNull();
    expect(screen.getByRole("button", { name: "1 de espadas" }).className).toContain("playable");
  });

  it("shows no end-of-mano banner: the points go on the scoreboard", () => {
    setup(makeView(), {
      busy: true,
      beat: { id: 6, seat: null, kind: "fin_mano", points: [0, 3], ms: 1600, think: 0 },
    });
    expect(screen.queryByText(/Fin de la mano/)).toBeNull();
  });
});
