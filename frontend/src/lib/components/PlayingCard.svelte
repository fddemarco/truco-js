<script lang="ts">
  import { CARD_BACK, cardName, cardSrc, COMODINES, type Suit } from "$lib/cards";

  type Props =
    | { number: number; suit: Suit; faceDown?: boolean; class?: string }
    | { comodin: 1 | 2; class?: string }
    | { faceDown: true; class?: string };

  let props: Props = $props();

  const image = $derived.by(() => {
    if ("comodin" in props) return { src: COMODINES[props.comodin - 1], alt: "Comodín" };
    if (props.faceDown || !("suit" in props)) return { src: CARD_BACK, alt: "Dorso" };
    return { src: cardSrc(props.number, props.suit), alt: cardName(props.number, props.suit) };
  });

  let failedSrc = $state<string | null>(null);
  const failed = $derived(failedSrc === image.src);

  function onError() {
    failedSrc = image.src;
    console.error(`Could not load card image ${image.src}`);
  }
</script>

{#if failed}
  <!-- The art is missing: still show which card it is. -->
  <div
    role="img"
    aria-label={image.alt}
    class="flex aspect-[2/3] w-24 items-center justify-center rounded-lg border-2 border-dashed border-slate-400 bg-white p-1 text-center text-xs text-slate-700 {props.class ??
      ''}"
  >
    {image.alt}
  </div>
{:else}
  <img
    src={image.src}
    alt={image.alt}
    width="200"
    height="300"
    draggable="false"
    onerror={onError}
    class="aspect-[2/3] h-auto w-24 select-none {props.class ?? ''}"
  />
{/if}
