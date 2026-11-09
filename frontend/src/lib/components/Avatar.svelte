<script lang="ts">
  import { untrack } from "svelte";
  import {
    avatarSrc,
    characterFor,
    type BodySpot,
    type Character,
    type Sena,
  } from "$lib/avatar/avatar";
  import { isDecoded, loadImage, preloadAvatars } from "$lib/avatar/preload";

  interface Props {
    /** The character, or a seat index (seat i → the i-th character). */
    character: Character | number;
    label: string;
    /** The seña being shown right now; the table clears it after its duration. */
    sena?: Sena;
    spot?: BodySpot;
    class?: string;
  }

  let { character, label, sena, spot, class: className = "" }: Props = $props();

  // A width from the caller replaces the default one (Tailwind's order would keep w-20).
  const size = $derived(/(^|\s)w-/.test(className) ? "" : "w-20");
  const id = $derived(typeof character === "number" ? characterFor(character) : character);
  const base = $derived(avatarSrc(id));
  const wanted = $derived(avatarSrc(id, sena, spot));

  // The play page preloads the seated characters already; this covers any other use.
  $effect(() => preloadAvatars([id]));

  // A missing seña image shows the neutral face; a missing neutral face shows the initial.
  let failedSrcs = $state<string[]>([]);
  const target = $derived(failedSrcs.includes(wanted) ? base : wanted);

  // The one <img> keeps showing the current face until the next one is decoded, then swaps.
  let src = $state(untrack(() => target));
  $effect(() => {
    const next = target;
    if (next === untrack(() => src) || isDecoded(next)) {
      src = next;
      return;
    }
    let live = true;
    loadImage(next).then(
      () => live && (src = next),
      () => live && fail(next),
    );
    return () => (live = false);
  });
  const failed = $derived(failedSrcs.includes(src));

  function fail(bad: string) {
    if (failedSrcs.includes(bad)) return;
    failedSrcs = [...failedSrcs, bad];
    console.error(`Could not load avatar image ${bad}`);
  }
</script>

<div role="img" aria-label={label} class="aspect-square {size} {className}">
  {#if failed}
    <div
      class="flex h-full w-full items-center justify-center rounded-full bg-slate-200 text-2xl font-bold text-slate-600"
    >
      {label.trim().charAt(0).toUpperCase()}
    </div>
  {:else}
    <img
      {src}
      alt=""
      width="512"
      height="512"
      draggable="false"
      data-variant={src === base ? "base" : "sena"}
      onerror={() => fail(src)}
      class="h-full w-full select-none object-contain"
    />
  {/if}
</div>
