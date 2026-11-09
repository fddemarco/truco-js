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

  // These use characters no other test renders: decoded images are cached for the page.
  it("keeps the current face until the seña image is decoded, so it never flashes blank", async () => {
    let decoded!: () => void;
    vi.stubGlobal(
      "Image",
      class extends Image {
        decode = () =>
          this.src.endsWith("/calculadora/sena_04.webp")
            ? new Promise<void>((resolve) => (decoded = resolve))
            : Promise.resolve();
      },
    );
    const { rerender } = render(Avatar, { character: 4, label: "Jugador 5" });

    await rerender({
      character: 4,
      label: "Jugador 5",
      sena: "sena_04",
      spot: "comisura_izquierda",
    });
    expect(img("Jugador 5")?.getAttribute("src")).toBe("/avatars/calculadora/base.webp");

    decoded();
    await vi.waitFor(() =>
      expect(img("Jugador 5")?.getAttribute("src")).toBe("/avatars/calculadora/sena_04.webp"),
    );
    vi.unstubAllGlobals();
  });

  it("stays on the neutral face and logs when a seña image cannot be decoded", async () => {
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "Image",
      class extends Image {
        decode = () =>
          this.src.endsWith("/fanfarron/sena_06.webp")
            ? Promise.reject(new Error("bad"))
            : Promise.resolve();
      },
    );
    const { rerender } = render(Avatar, { character: 5, label: "Jugador 6" });
    await rerender({ character: 5, label: "Jugador 6", sena: "sena_06", spot: "labios" });

    await vi.waitFor(() =>
      expect(log).toHaveBeenCalledWith(
        "Could not load avatar image /avatars/fanfarron/sena_06.webp",
      ),
    );
    expect(img("Jugador 6")?.getAttribute("src")).toBe("/avatars/fanfarron/base.webp");
    vi.unstubAllGlobals();
  });
});
