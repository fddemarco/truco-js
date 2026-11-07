import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import Avatar from "./Avatar.svelte";

describe("Avatar", () => {
  it("renders the seat's avatar with its label", () => {
    render(Avatar, { look: 2, label: "Jugador 3" });
    const avatar = screen.getByRole("img", { name: "Jugador 3" });
    expect(avatar.querySelector("svg")?.getAttribute("data-sena")).toBe("");
  });

  it("shows a seña and clears it when the prop goes away", async () => {
    const { container, rerender } = render(Avatar, {
      look: 0,
      label: "Jugador 1",
      sena: "sena_01",
    });
    expect(container.querySelector('[data-part="cejas"]')?.getAttribute("data-state")).toBe(
      "arriba",
    );
    await rerender({ look: 0, label: "Jugador 1", sena: undefined });
    expect(container.querySelector('[data-part="cejas"]')?.getAttribute("data-state")).toBe(
      "normal",
    );
  });
});
