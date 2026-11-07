import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import Avatar from "./Avatar.svelte";

const img = (label: string) => screen.getByRole("img", { name: label }).querySelector("img");

describe("Avatar", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the seat's character with its label", () => {
    render(Avatar, { character: 2, label: "Jugador 3" });
    expect(img("Jugador 3")?.getAttribute("src")).toBe("/avatars/roca/base.webp");
  });

  it("shows a seña and clears it when the prop goes away", async () => {
    const { rerender } = render(Avatar, {
      character: 0,
      label: "Jugador 1",
      sena: "sena_12",
      spot: "nariz",
    });
    expect(img("Jugador 1")?.getAttribute("src")).toBe("/avatars/tiburon/sena_12.webp");
    await rerender({ character: 0, label: "Jugador 1", sena: undefined, spot: undefined });
    expect(img("Jugador 1")?.getAttribute("src")).toBe("/avatars/tiburon/base.webp");
  });

  it("shows the neutral face when a seña image fails to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(Avatar, { character: 3, label: "Jugador 4", sena: "sena_05", spot: "labio_inferior" });

    await fireEvent.error(img("Jugador 4")!);

    expect(img("Jugador 4")?.getAttribute("src")).toBe("/avatars/novato/base.webp");
  });

  it("falls back to the initial and logs when the image fails to load", async () => {
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    render(Avatar, { character: 1, label: "ana" });

    await fireEvent.error(img("ana")!);

    const avatar = screen.getByRole("img", { name: "ana" });
    expect(avatar.querySelector("img")).toBeNull();
    expect(avatar.textContent?.trim()).toBe("A");
    expect(log).toHaveBeenCalledWith("Could not load avatar image /avatars/maniaca/base.webp");
  });
});
