<script lang="ts">
  import { CARD_BACK, cardName, cardSrc, COMODINES, type Suit } from "$lib/cards";

  type Common = { class?: string; style?: string };
  type Props =
    | ({ number: number; suit: Suit; faceDown?: boolean } & Common)
    | ({ comodin: 1 | 2 } & Common)
    | ({ faceDown: true } & Common);

  let props: Props = $props();

  const image = $derived.by(() => {
    if ("comodin" in props) return { src: COMODINES[props.comodin - 1], alt: "Comodín" };
    if (props.faceDown || !("suit" in props)) return { src: CARD_BACK, alt: "Dorso" };
    return { src: cardSrc(props.number, props.suit), alt: cardName(props.number, props.suit) };
  });

  // A width from the caller replaces the default one (both would set `width`, and the
  // default would win in the stylesheet's order).
  const size = $derived(/(^|\s)w-/.test(props.class ?? "") || props.style ? "" : "w-24");

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
    style={props.style}
    class="flex aspect-[2/3] {size} items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-slate-400 bg-white p-0.5 text-center text-[0.55rem] leading-tight text-slate-700 {props.class ??
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
    style={props.style}
    class="aspect-[2/3] h-auto {size} select-none {props.class ?? ''}"
  />
{/if}
