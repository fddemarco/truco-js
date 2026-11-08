<script lang="ts">
  import type { CardModel } from "$lib/api/client";
  import { cardName, type Suit } from "$lib/cards";
  import { fanLayout, fanWidth } from "$lib/game";
  import PlayingCard from "./PlayingCard.svelte";

  interface Props {
    /** Face-up cards (the viewer's), or a number of face-down ones (everyone else's). */
    cards: CardModel[] | number;
    /** Card width in px. */
    width: number;
    /** Fan the cards out (the viewer's own hand); otherwise they sit closed. */
    open?: boolean;
    playable?: (card: CardModel) => boolean;
    onPlay?: (card: CardModel) => void;
    label?: string;
  }

  let { cards, width, open = false, playable = () => false, onPlay, label }: Props = $props();

  const faces = $derived(typeof cards === "number" ? null : cards);
  const n = $derived(typeof cards === "number" ? cards : cards.length);
  const spread = $derived(open);
  const layout = $derived(fanLayout(n, spread));
  const height = $derived(width * 1.55);
</script>

{#if n > 0}
  <div
    class="hand relative"
    style="width: {fanWidth(n, spread) * width}px; height: {height + width * 0.25}px"
    role="group"
    aria-label={label}
    data-open={spread}
    data-testid="hand"
  >
    {#each layout as pos, i (faces ? `${faces[i].number}-${faces[i].suit}` : i)}
      {@const card = faces?.[i]}
      {@const can = card ? playable(card) : false}
      <div
        class="slot absolute top-0"
        style="left: {pos.x * width}px; transform: translateY({pos.lift * width +
          width * 0.12}px) rotate({pos.rotate}deg); z-index: {i}"
      >
        {#if card}
          <button
            type="button"
            class="hand-card relative block rounded-[4%/2.7%] {can ? 'playable' : ''}"
            disabled={!can}
            aria-label={cardName(card.number, card.suit as Suit)}
            onclick={() => onPlay?.(card)}
          >
            <PlayingCard
              number={card.number}
              suit={card.suit as Suit}
              class="shadow-lg"
              style="width: {width}px"
            />
          </button>
        {:else}
          <PlayingCard faceDown class="shadow-md" style="width: {width}px" />
        {/if}
      </div>
    {/each}
  </div>
{/if}

<style>
  .hand,
  .slot {
    transition:
      width 0.25s ease-out,
      left 0.25s ease-out,
      transform 0.25s ease-out;
  }
  /* Not `.card`: that is the white panel in app.css. */
  .hand-card {
    transition: transform 0.15s ease-out;
  }
  .hand-card.playable {
    box-shadow:
      0 0 0 3px #34d399,
      0 8px 18px rgba(0, 0, 0, 0.35);
  }
  .hand-card.playable:hover,
  .hand-card.playable:focus-visible {
    transform: translateY(-14px);
  }
  @media (prefers-reduced-motion: reduce) {
    .hand,
    .slot,
    .hand-card {
      transition: none;
    }
  }
</style>
