import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { GameView } from "$lib/api/client";
import GameOver from "./GameOver.svelte";

const view = {
  team_names: ["Los Pumas", "Los Teros"],
  score: [30, 22],
  result: { kind: "deportivo", winner: 0 },
  stats: [
    { key: "manos", seat: null, value: 12, mano: null, cards: [] },
    {
      key: "strongest_hand",
      seat: 3,
      value: 37,
      mano: 4,
      cards: [
        { number: 1, suit: "espada" },
        { number: 1, suit: "basto" },
        { number: 7, suit: "espada" },
      ],
    },
    { key: "liar", seat: 0, value: 3, mano: null, cards: [] },
    { key: "something_new", seat: 1, value: 1, mano: null, cards: [] },
  ],
} as unknown as GameView;

function setup(myTeam: number | null) {
  const onClose = vi.fn();
  render(GameOver, { view, myTeam, nameOf: (s: number) => (s === 0 ? "Vos" : `P${s}`), onClose });
  return onClose;
}

describe("GameOver", () => {
  it("celebrates a win, with the final score and the facts in words", () => {
    setup(0);
    expect(screen.getByTestId("game-over").dataset.outcome).toBe("win");
    expect(screen.getByRole("heading", { name: "¡Ganamos!" })).toBeTruthy();
    expect(screen.getByTestId("final-score").textContent).toMatch(/Los Pumas 30.*22 Los Teros/s);
    const facts = screen.getByTestId("facts").textContent ?? "";
    expect(facts).toContain("Se jugaron 12 manos.");
    expect(facts).toContain("P3 en la mano 4, con 1 de espadas, 1 de bastos, 7 de espadas");
    expect(facts).toContain("El más mentiroso: Vos (faroles: 3).");
    expect(screen.getAllByRole("listitem")).toHaveLength(3); // an unknown fact is left out
  });

  it("mourns a loss", () => {
    setup(1);
    expect(screen.getByTestId("game-over").dataset.outcome).toBe("lose");
    expect(screen.getByRole("heading", { name: "Perdimos" })).toBeTruthy();
  });

  it("names the winner for a spectator", () => {
    setup(null);
    expect(screen.getByTestId("game-over").dataset.outcome).toBe("neutral");
    expect(screen.getByRole("heading", { name: "Ganó Los Pumas" })).toBeTruthy();
  });

  it("offers a new game, home, and going back to the table", async () => {
    const onClose = setup(0);
    expect(screen.getByRole("link", { name: "Nueva partida" }).getAttribute("href")).toBe("/play");
    expect(screen.getByRole("link", { name: "Inicio" }).getAttribute("href")).toBe("/");
    await fireEvent.click(screen.getByRole("button", { name: "Ver la mesa" }));
    expect(onClose).toHaveBeenCalled();
  });
});
