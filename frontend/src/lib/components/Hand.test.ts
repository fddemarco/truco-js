import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import Hand from "./Hand.svelte";

const cards = [
  { number: 1, suit: "espada" },
  { number: 4, suit: "oro" },
  { number: 7, suit: "copa" },
];

describe("Hand", () => {
  it("keeps a player's hand closed on hover: only played cards spread out", async () => {
    render(Hand, { cards: 3, width: 40 });
    const hand = screen.getByTestId("hand");
    const closed = parseFloat(hand.style.width);
    await fireEvent.mouseEnter(hand);
    expect(hand.dataset.open).toBe("false");
    expect(parseFloat(hand.style.width)).toBe(closed);
  });

  it("plays only the playable cards", async () => {
    const onPlay = vi.fn();
    render(Hand, {
      cards,
      width: 80,
      open: true,
      playable: (c) => c.number === 4,
      onPlay,
    });
    expect(
      (screen.getByRole("button", { name: "1 de espadas" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "4 de oros" }));
    expect(onPlay).toHaveBeenCalledWith(cards[1]);
    expect(document.querySelector("kbd")).toBeNull(); // key hints live in "how to play"
  });
});
