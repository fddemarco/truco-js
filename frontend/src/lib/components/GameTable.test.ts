import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GameAction, GameView } from "$lib/api/client";
import { avatarSrc, characterFor } from "$lib/avatar/avatar";
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
      kind: i === 0 ? "human" : "bot",
      joined: true,
      in_play: true,
      active: true,
      cards_left: 3,
      shown: [],
    })),
    score: [3, 7],
    hand_number: 2,
    hand_kind: "redonda",
    dealer: 5,
    mano: 0,
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
  const onDeal = vi.fn();
  const onSena = vi.fn();
  render(GameTable, { view, viewer: 0, onAct, onDeal, onSena, ...extra });
  return { onAct, onDeal, onSena };
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

  it("deals the next mano", async () => {
    const { onDeal } = setup(makeView({ can_deal: true, actions: [] }));
    await fireEvent.click(screen.getByRole("button", { name: "Siguiente mano" }));
    expect(onDeal).toHaveBeenCalled();
  });

  it("shows the score, the moves and the result", () => {
    setup(makeView({ result: { kind: "deportivo", winner: 1 }, score: [22, 30] }));
    expect(screen.getByTestId("score-1").textContent).toBe("30");
    expect(screen.getByTestId("events").textContent).toContain("P1: Truco");
    expect(screen.getByRole("status").textContent).toContain("equipo 2");
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

  it("shows the seña on the signaller's avatar while it lasts", () => {
    const now = Date.now();
    const view = makeView({
      mode: "interactive",
      server_ms: now,
      senas: [
        {
          seat: 3,
          sena: "sena_02",
          spot: "ojo_derecho",
          target: null,
          start_ms: now - 100,
          duration_ms: 1000,
        },
      ],
    });
    setup(view);
    const avatar = (seat: number) =>
      screen.getByTestId(`seat-${seat}`).querySelector("img[data-variant]")?.getAttribute("src");
    expect(avatar(3)).toBe(avatarSrc(characterFor(3), "sena_02"));
    expect(avatar(1)).toBe(avatarSrc(characterFor(1)));
  });
});
