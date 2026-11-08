import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import PlayingCard from "./PlayingCard.svelte";

describe("PlayingCard", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows the card face with its Spanish name", () => {
    render(PlayingCard, { number: 1, suit: "espada" });
    const img = screen.getByRole("img", { name: "1 de espadas" });
    expect(img.tagName).toBe("IMG");
    expect(img.getAttribute("src")).toBe("/cards/1-espada.webp");
  });

  it("hides the face when face down", () => {
    render(PlayingCard, { number: 7, suit: "oro", faceDown: true });
    const img = screen.getByRole("img", { name: "Dorso" });
    expect(img.getAttribute("src")).toBe("/cards/dorso.webp");
  });

  it("shows a comodín", () => {
    render(PlayingCard, { comodin: 2 });
    expect(screen.getByRole("img", { name: "Comodín" }).getAttribute("src")).toBe(
      "/cards/comodin-2.webp",
    );
  });

  it("falls back to the card name and logs when the image fails to load", async () => {
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    render(PlayingCard, { number: 12, suit: "copa" });

    await fireEvent.error(screen.getByRole("img"));

    const fallback = screen.getByRole("img", { name: "12 de copas" });
    expect(fallback.tagName).toBe("DIV");
    expect(fallback.textContent?.trim()).toBe("12 de copas");
    expect(log).toHaveBeenCalledWith("Could not load card image /cards/12-copa.webp");
  });

  it("retries when the card changes after a failed load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { rerender } = render(PlayingCard, { number: 12, suit: "copa" });
    await fireEvent.error(screen.getByRole("img"));

    await rerender({ number: 3, suit: "oro" });

    const img = screen.getByRole("img", { name: "3 de oros" });
    expect(img.tagName).toBe("IMG");
  });

  it("takes the caller's width instead of the default one", () => {
    render(PlayingCard, { number: 1, suit: "espada", class: "w-12" });
    const img = screen.getByRole("img", { name: "1 de espadas" });
    expect(img.classList.contains("w-12")).toBe(true);
    expect(img.classList.contains("w-24")).toBe(false);
  });
});
