<script lang="ts">
  import { untrack } from "svelte";
  import { Tween } from "svelte/motion";
  import { cubicOut } from "svelte/easing";
  import type { GameView } from "$lib/api/client";
  import { play } from "$lib/audio.svelte";
  import { FOSFORO } from "$lib/cards";
  import { tally } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";

  interface Props {
    view: GameView;
    /** The viewer's team, if they play. */
    myTeam: number | null;
    nameOf: (seat: number) => string;
  }

  let { view, myTeam, nameOf }: Props = $props();

  // The numbers count up to the new score; the team that scored pulses.
  const tween = () => new Tween(0, { duration: 700, easing: cubicOut });
  const shown = [tween(), tween()];
  let pulse = $state<[number, number]>([0, 0]);
  let last: number[] | null = null;
  $effect(() => {
    const score = [view.score[0], view.score[1]];
    untrack(() => {
      score.forEach((s, team) => {
        if (last && s > last[team]) {
          pulse[team] += 1;
          play("fosforo");
        }
        shown[team].set(s, last ? undefined : { duration: 0 });
      });
    });
    last = score;
  });

  // Each fósforo of a square of five: four sides, then the diagonal.
  // The box is 24 px, a fósforo 4×24 px: rotating one about its centre lays it across.
  const SIDES = [
    "left: 0; top: 0",
    "left: calc(50% - 2px); top: -50%; transform: rotate(90deg)",
    "left: calc(100% - 4px); top: 0",
    "left: calc(50% - 2px); top: 50%; transform: rotate(90deg)",
    "left: calc(50% - 2px); top: 0; transform: rotate(45deg) scaleY(1.3)",
  ];
  const TEAM = [
    { bar: "from-indigo-500 to-indigo-700", ring: "ring-indigo-300", text: "text-indigo-100" },
    { bar: "from-rose-500 to-rose-700", ring: "ring-rose-300", text: "text-rose-100" },
  ];
</script>

<div class="grid grid-cols-[1fr_auto_1fr] items-stretch gap-3" data-testid="scoreboard">
  {#each [0, 1] as team (team)}
    {@const score = view.score[team]}
    {@const squares = tally(score)}
    {@const players = view.seats.filter((s) => s.team === team)}
    <div
      class="group relative flex items-center gap-3 rounded-2xl bg-gradient-to-br {TEAM[team]
        .bar} px-4 py-2 text-white shadow-lg {myTeam === team
        ? `ring-4 ${TEAM[team].ring}`
        : ''} {team === 1 ? 'order-3 flex-row-reverse text-right' : ''}"
      role="group"
      aria-label={view.team_names[team]}
    >
      <div class="min-w-0">
        <p class="truncate text-sm font-bold">{view.team_names[team]}</p>
        {#if myTeam === team}
          <p class="text-[0.65rem] font-semibold tracking-wide uppercase {TEAM[team].text}">
            {t("game.yourTeam")}
          </p>
        {/if}
        <p class="text-[0.65rem] {TEAM[team].text}">{score >= 15 ? "buenas" : "malas"}</p>
      </div>
      {#key pulse[team]}
        <span
          class="score font-mono text-4xl font-black tabular-nums drop-shadow"
          data-testid="score-{team}"
          data-pulse={pulse[team] > 0}>{Math.round(shown[team].current)}</span
        >
      {/key}
      <!-- fósforos: malas | buenas -->
      <div
        class="ml-auto flex items-center gap-1.5 {team === 1
          ? 'mr-auto ml-0 flex-row-reverse'
          : ''}"
        aria-hidden="true"
      >
        {#each squares as count, i (i)}
          {#if i === 3}<span class="mx-0.5 h-8 w-px bg-white/40"></span>{/if}
          <span class="relative h-6 w-6">
            {#each SIDES.slice(0, count) as side, j (j)}
              <img
                src={FOSFORO}
                alt=""
                class="fosforo absolute h-6 w-1"
                style="{side}; --d: {j * 60}ms"
              />
            {/each}
          </span>
        {/each}
      </div>

      <!-- who plays for this team -->
      <div
        class="pointer-events-none absolute top-full z-40 mt-2 hidden w-56 rounded-xl bg-white p-2 text-slate-900 shadow-xl group-hover:block {team ===
        1
          ? 'right-0'
          : 'left-0'}"
        role="tooltip"
      >
        {#each players as p (p.seat)}
          <div class="flex items-center gap-2 py-1 text-left text-sm">
            <span class="rounded-full ring-2 {TEAM[team].ring}">
              <Avatar character={p.character} label={p.name} class="w-9" />
            </span>
            <span class="font-semibold">{nameOf(p.seat)}</span>
            <span class="ml-auto text-xs text-slate-500">{t("game.number", { n: p.number })}</span>
          </div>
        {/each}
      </div>
    </div>
  {/each}
  <div class="order-2 flex flex-col items-center justify-center text-center text-xs text-slate-600">
    {#if view.hand_kind}
      <span class="font-semibold">{t("game.handNumber", { n: view.hand_number })}</span>
      <span
        class="mt-0.5 rounded-full px-2 py-0.5 font-bold text-white {view.hand_kind === 'pica_pica'
          ? 'bg-amber-600'
          : 'bg-emerald-700'}">{view.hand_kind === "pica_pica" ? "Pica-pica" : "Mano redonda"}</span
      >
    {/if}
  </div>
</div>

<style>
  .fosforo {
    transform-origin: center;
    animation: strike 0.45s ease-out var(--d) both;
  }
  @keyframes strike {
    from {
      opacity: 0;
      filter: brightness(2.5);
      scale: 1.6;
    }
  }
  .score[data-pulse="true"] {
    animation: pulse 0.6s ease-out;
  }
  @keyframes pulse {
    40% {
      transform: scale(1.35);
      color: #fde68a;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .fosforo,
    .score {
      animation: none !important;
    }
  }
</style>
