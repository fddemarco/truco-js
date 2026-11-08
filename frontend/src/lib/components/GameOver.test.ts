import { render, screen, within } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
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
  render(GameOver, { view, myTeam, nameOf: (s: number) => (s === 0 ? "Vos" : `P${s}`) });
}

describe("GameOver", () => {
  it("celebrates a win, with the final score and the facts as medallions", () => {
    setup(0);
    expect(screen.getByTestId("game-over").dataset.outcome).toBe("win");
    expect(screen.getByRole("heading", { name: "¡Ganamos!" })).toBeTruthy();
    expect(screen.getByTestId("final-score").textContent).toMatch(/Los Pumas 30.*22 Los Teros/s);
    expect(screen.getByTestId("manos").textContent).toContain("12 manos");
    // a short title, who and the number or the cards; an unknown fact is left out
    const facts = within(screen.getByTestId("facts")).getAllByRole("listitem");
    expect(facts).toHaveLength(2);
    const liar = screen.getByTestId("fact-liar");
    expect(liar.textContent).toContain("Mentiroso");
    expect(liar.textContent).toContain("Vos");
    expect(liar.textContent).toContain("3");
    const hand = screen.getByTestId("fact-strongest_hand");
    expect(hand.querySelectorAll("img[alt='1 de espadas']")).toHaveLength(1);
  });

  it("keeps each fact's sentence as its tooltip", () => {
    setup(0);
    const liar = screen.getByTestId("fact-liar");
    const tip = document.getElementById(liar.getAttribute("aria-describedby")!);
    expect(tip?.getAttribute("role")).toBe("tooltip");
    expect(tip?.textContent).toBe("El más mentiroso: Vos (faroles: 3).");
    expect(screen.getByTestId("fact-strongest_hand").textContent).toContain(
      "P3 en la mano 4, con 1 de espadas, 1 de bastos, 7 de espadas",
    );
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

  it("offers a new game or home, and no way back to the table", () => {
    setup(0);
    expect(screen.getByRole("link", { name: "Nueva partida" }).getAttribute("href")).toBe("/play");
    expect(screen.getByRole("link", { name: "Inicio" }).getAttribute("href")).toBe("/");
    expect(screen.queryByRole("button")).toBeNull();
  });
});
