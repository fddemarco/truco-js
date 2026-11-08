import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { GameView } from "$lib/api/client";
import { CHARACTERS } from "$lib/avatar/avatar";
import Lobby from "./Lobby.svelte";

function lobby(seats: Partial<GameView["seats"][number]>[], started = false): GameView {
  return {
    started,
    team_names: ["A", "B"],
    seats: seats.map((s, i) => ({
      seat: i,
      team: i % 2,
      name: `P${i}`,
      character: CHARACTERS[i],
      kind: "human",
      joined: false,
      online: false,
      ...s,
    })),
  } as unknown as GameView;
}

const props = (view: GameView, over: Record<string, unknown> = {}) => ({
  view,
  mySeats: [],
  isHost: false,
  url: "http://x/play/g1",
  onJoin: vi.fn(),
  onReset: vi.fn(),
  ...over,
});

describe("Lobby", () => {
  it("lets a newcomer join an open seat", async () => {
    const view = lobby([{ joined: true, online: true }, {}, { kind: "bot", joined: true }]);
    const p = props(view);
    render(Lobby, p);
    const buttons = screen.getAllByRole("button", { name: "Unirme" });
    expect(buttons).toHaveLength(1);
    await fireEvent.click(buttons[0]);
    expect(p.onJoin).toHaveBeenCalledWith(1);
  });

  it("offers to free other players' seats only to the host", async () => {
    const view = lobby([{ joined: true, online: true }, { joined: true }]);
    render(Lobby, props(view, { mySeats: [0] }));
    expect(screen.queryByRole("button", { name: "Liberar asiento" })).toBeNull();
  });

  it("the host frees a seat, never their own", async () => {
    const view = lobby([{ joined: true, online: true }, { joined: true }]);
    const p = props(view, { mySeats: [0], isHost: true });
    render(Lobby, p);
    const free = screen.getAllByRole("button", { name: "Liberar asiento" });
    expect(free).toHaveLength(1);
    await fireEvent.click(free[0]);
    expect(p.onReset).toHaveBeenCalledWith(1);
  });

  it("says when there's no seat left", () => {
    render(Lobby, props(lobby([{ joined: true }], true)));
    expect(screen.getByText(/No quedan asientos libres/)).toBeTruthy();
  });
});
