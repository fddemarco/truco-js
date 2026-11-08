<script lang="ts">
  import PlayingCard from "./PlayingCard.svelte";

  interface Props {
    /** idle: a resting deck. shuffling: halves riffling. cutting: the top half goes under. */
    state?: "idle" | "shuffling" | "cutting";
    class?: string;
  }

  let { state = "idle", class: className = "w-9" }: Props = $props();

  // Layers make it look thick: each card a hair up and left of the one below.
  const BOTTOM = [0, 1, 2, 3];
  const TOP = [4, 5, 6];
</script>

<div class="mazo relative {className}" data-state={state} data-testid="mazo-deck">
  <!-- the bottom layer sits in the flow and gives the deck its size -->
  <div class="invisible"><PlayingCard faceDown class="w-full" /></div>
  <div class="half bottom absolute inset-0">
    {#each BOTTOM as i (i)}
      <div class="layer absolute inset-0" style="--i: {i}">
        <PlayingCard faceDown class="w-full" />
      </div>
    {/each}
  </div>
  <div class="half top absolute inset-0">
    {#each TOP as i (i)}
      <div class="layer absolute inset-0" style="--i: {i}">
        <PlayingCard faceDown class="w-full" />
      </div>
    {/each}
  </div>
</div>

<style>
  .layer {
    transform: translate(calc(var(--i) * -1.2px), calc(var(--i) * -1.4px));
    filter: drop-shadow(0 1px 0.5px rgb(0 0 0 / 0.35));
  }
  .mazo {
    filter: drop-shadow(0 6px 6px rgb(0 0 0 / 0.35));
  }
  .top {
    z-index: 2;
  }
  .bottom {
    z-index: 1;
  }

  /* Riffle: the halves split to the sides and fall back together, over and over. */
  .mazo[data-state="shuffling"] .top {
    animation: riffle-top 0.9s ease-in-out infinite;
  }
  .mazo[data-state="shuffling"] .bottom {
    animation: riffle-bottom 0.9s ease-in-out infinite;
  }
  @keyframes riffle-top {
    0%,
    100% {
      transform: none;
    }
    35% {
      transform: translateX(55%) rotate(10deg);
    }
    60% {
      transform: translateX(10%) rotate(2deg);
    }
  }
  @keyframes riffle-bottom {
    0%,
    100% {
      transform: none;
    }
    35% {
      transform: translateX(-45%) rotate(-8deg);
    }
    60% {
      transform: translateX(-8%) rotate(-2deg);
    }
  }

  /* Cut: the top half is lifted aside, then the rest goes on top of it. */
  .mazo[data-state="cutting"] .top {
    animation: cut 0.7s ease-in-out both;
  }
  @keyframes cut {
    0% {
      transform: none;
      z-index: 2;
    }
    40% {
      transform: translate(115%, -20%) rotate(6deg);
      z-index: 2;
    }
    55% {
      transform: translate(115%, 0);
      z-index: 0;
    }
    100% {
      transform: none;
      z-index: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .mazo .half {
      animation: none !important;
    }
  }
</style>
