<script lang="ts">
  import {
    avatarSrc,
    avatarVariants,
    characterFor,
    type BodySpot,
    type Character,
    type Sena,
  } from "$lib/avatar/avatar";

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

  // Señas last about half a second: load every variant up front so none flashes blank.
  $effect(() => {
    for (const s of avatarVariants(id)) new Image().src = s;
  });

  // A missing seña image shows the neutral face; a missing neutral face shows the initial.
  let failedSrcs = $state<string[]>([]);
  const src = $derived(failedSrcs.includes(wanted) ? base : wanted);
  const failed = $derived(failedSrcs.includes(src));

  function onError() {
    failedSrcs = [...failedSrcs, src];
    console.error(`Could not load avatar image ${src}`);
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
    {#key src}
      <img
        {src}
        alt=""
        width="512"
        height="512"
        draggable="false"
        data-variant={sena ? "sena" : "base"}
        onerror={onError}
        class="avatar h-full w-full select-none object-contain"
      />
    {/key}
  {/if}
</div>

<style>
  @media (prefers-reduced-motion: no-preference) {
    .avatar {
      animation: sena-in 0.12s ease-out;
    }
  }
  @keyframes sena-in {
    from {
      opacity: 0.6;
    }
  }
</style>
