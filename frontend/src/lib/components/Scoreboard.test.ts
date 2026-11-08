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
  results: [],
  envido: null,
  envido_calls: [],
  truco_level: 0,
  truco_accepted: 0,
  seats: Array.from({ length: 6 }, (_, i) => ({
    seat: i,
    team: i % 2,
    number: 1,
    name: `P${i}`,
    character: CHARACTERS[i],
  })),
} as unknown as GameView;

describe("Scoreboard", () => {
  it("shows each score as squares of five strokes, the team names, and who plays for each", () => {
    render(Scoreboard, { view, myTeam: 0, nameOf: (s: number) => `P${s}` });
    const pumas = screen.getByRole("group", { name: "Los Pumas" });
    // 13 = two full squares (four sides and the diagonal) and three strokes, same for both teams
    expect(pumas.querySelectorAll("path.stroke")).toHaveLength(13);
    expect(screen.getByTestId("score-0").textContent).toBe("13");
    expect(within(pumas).getByText("P2")).toBeTruthy(); // in the hover card
    const teros = screen.getByRole("group", { name: "Los Teros" });
    expect(teros.querySelectorAll("path.stroke")).toHaveLength(4);
  });

  it("shows the points scored as +N by the score, then counts up to them", async () => {
    const { rerender } = render(Scoreboard, { view, myTeam: 0, nameOf: (s: number) => `P${s}` });
    expect(screen.queryByTestId("gain-1")).toBeNull();
    await rerender({ view: { ...view, score: [13, 7] } as GameView });
    expect(screen.getByTestId("gain-1").textContent).toBe("+3");
    expect(screen.queryByTestId("gain-0")).toBeNull();
  });

  it("marks the envido and truco of the mano, from nothing to accepted or not", () => {
    render(Scoreboard, {
      view: {
        ...view,
        results: [],
        envido: { calls: ["envido"], accepted: false, points: 1 },
        envido_calls: ["envido"],
        truco_level: 2,
        truco_accepted: 2,
      } as unknown as GameView,
      myTeam: 0,
      nameOf: (s: number) => `P${s}`,
    });
    expect(screen.getByTestId("marker-envido").dataset.state).toBe("rejected");
    const truco = screen.getByTestId("marker-truco");
    expect(truco.dataset.state).toBe("accepted");
    expect(truco.textContent).toContain("RT");
  });
});
