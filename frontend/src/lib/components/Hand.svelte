<script lang="ts">
  import type { CardModel } from "$lib/api/client";
  import { cardName, type Suit } from "$lib/cards";
  import { fanLayout, fanWidth } from "$lib/game";
  import { cardKeyHint } from "$lib/keys";
  import { bindings } from "$lib/profile.svelte";
  import PlayingCard from "./PlayingCard.svelte";

  interface Props {
    /** Face-up cards (the viewer's), or a number of face-down ones (everyone else's). */
    cards: CardModel[] | number;
    /** Card width in px. */
    width: number;
    /** Keep the fan open (e.g. the viewer's turn); otherwise it opens on hover. */
    open?: boolean;
    playable?: (card: CardModel) => boolean;
    onPlay?: (card: CardModel) => void;
    /** Show the keyboard letter on each card. */
    keys?: boolean;
    label?: string;
  }

  let {
    cards,
    width,
    open = false,
    playable = () => false,
    onPlay,
    keys = false,
    label,
  }: Props = $props();

  const bound = $derived(bindings());
  let hovered = $state(false);
  const faces = $derived(typeof cards === "number" ? null : cards);
  const n = $derived(typeof cards === "number" ? cards : cards.length);
  const spread = $derived(open || hovered);
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
    onmouseenter={() => (hovered = true)}
    onmouseleave={() => (hovered = false)}
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
            class="card relative block rounded-lg {can ? 'playable' : ''}"
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
            {#if keys && can && cardKeyHint(i, bound)}
              <kbd
                class="absolute -top-2 -left-2 rounded bg-slate-900/85 px-1.5 text-[0.65rem] font-bold text-white shadow"
                >{cardKeyHint(i, bound)}</kbd
              >
            {/if}
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
  .card {
    transition: transform 0.15s ease-out;
  }
  .card.playable {
    box-shadow:
      0 0 0 3px #34d399,
      0 8px 18px rgba(0, 0, 0, 0.35);
  }
  .card.playable:hover,
  .card.playable:focus-visible {
    transform: translateY(-14px);
  }
  @media (prefers-reduced-motion: reduce) {
    .hand,
    .slot,
    .card {
      transition: none;
    }
  }
</style>
