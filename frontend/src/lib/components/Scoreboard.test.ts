import { render, screen, within } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import type { GameView } from "$lib/api/client";
import { CHARACTERS } from "$lib/avatar/avatar";
import Scoreboard from "./Scoreboard.svelte";

const view = {
  score: [13, 4],
  team_names: ["Los Pumas", "Los Teros"],
  hand_kind: "redonda",
  hand_number: 3,
  seats: Array.from({ length: 6 }, (_, i) => ({
    seat: i,
    team: i % 2,
    number: 1,
    name: `P${i}`,
    character: CHARACTERS[i],
  })),
} as unknown as GameView;

describe("Scoreboard", () => {
  it("shows each score as fósforos, the team names, and who plays for each", () => {
    render(Scoreboard, { view, myTeam: 0, nameOf: (s: number) => `P${s}` });
    const pumas = screen.getByRole("group", { name: "Los Pumas" });
    expect(pumas.querySelectorAll("img.fosforo")).toHaveLength(13);
    expect(screen.getByTestId("score-0").textContent).toBe("13");
    expect(within(pumas).getByText("Tu equipo")).toBeTruthy();
    expect(within(pumas).getByText("P2")).toBeTruthy(); // in the hover card
    const teros = screen.getByRole("group", { name: "Los Teros" });
    expect(teros.querySelectorAll("img.fosforo")).toHaveLength(4);
    expect(within(teros).queryByText("Tu equipo")).toBeNull();
  });
});
