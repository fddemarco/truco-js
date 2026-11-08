import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import Hand from "./Hand.svelte";

const cards = [
  { number: 1, suit: "espada" },
  { number: 4, suit: "oro" },
  { number: 7, suit: "copa" },
];

describe("Hand", () => {
  it("opens into a fan on hover", async () => {
    render(Hand, { cards: 3, width: 40 });
    const hand = screen.getByTestId("hand");
    expect(hand.dataset.open).toBe("false");
    const closed = parseFloat(hand.style.width);
    await fireEvent.mouseEnter(hand);
    expect(hand.dataset.open).toBe("true");
    expect(parseFloat(hand.style.width)).toBeGreaterThan(closed);
    await fireEvent.mouseLeave(hand);
    expect(hand.dataset.open).toBe("false");
  });

  it("plays only the playable cards, and shows their keys", async () => {
    const onPlay = vi.fn();
    render(Hand, {
      cards,
      width: 80,
      open: true,
      keys: true,
      playable: (c) => c.number === 4,
      onPlay,
    });
    expect(
      (screen.getByRole("button", { name: "1 de espadas" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    await fireEvent.click(screen.getByRole("button", { name: "4 de oros" }));
    expect(onPlay).toHaveBeenCalledWith(cards[1]);
    expect(screen.getByText("S")).toBeTruthy();
  });
});
