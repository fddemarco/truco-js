<script lang="ts">
  import { untrack } from "svelte";
  import { Tween } from "svelte/motion";
  import { cubicOut } from "svelte/easing";
  import type { GameView } from "$lib/api/client";
  import { FOSFORO } from "$lib/cards";
  import { status, tally } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";

  interface Props {
    view: GameView;
    /** The viewer's team, if they play. */
    myTeam: number | null;
    nameOf: (seat: number) => string;
  }

  let { view, myTeam, nameOf }: Props = $props();

  // Points scored show as a coloured "+N" by the score; then the number counts up to it.
  const DELTA_MS = 650;
  const tween = () => new Tween(0, { duration: 600, easing: cubicOut });
  const shown = [tween(), tween()];
  let gained = $state<{ id: number; points: number }[]>([
    { id: 0, points: 0 },
    { id: 0, points: 0 },
  ]);
  let last: number[] | null = null;
  $effect(() => {
    const score = [view.score[0], view.score[1]];
    untrack(() => {
      score.forEach((s, team) => {
        const before = last?.[team];
        if (before !== undefined && s > before) {
          gained[team] = { id: gained[team].id + 1, points: s - before };
          shown[team].set(s, { delay: DELTA_MS });
        } else shown[team].set(s, { duration: 0 });
      });
    });
    last = score;
  });

  const mano = $derived(status(view));

  // Each fósforo of a square of five: four sides, then the diagonal.
  // The box is 18 px, a fósforo 3×18 px: rotating one about its centre lays it across.
  const SIDES = [
    "left: 0; top: 0",
    "left: calc(50% - 1.5px); top: -50%; transform: rotate(90deg)",
    "left: calc(100% - 3px); top: 0",
    "left: calc(50% - 1.5px); top: 50%; transform: rotate(90deg)",
    "left: calc(50% - 1.5px); top: 0; transform: rotate(45deg) scaleY(1.3)",
  ];
  const TEAM = [
    { dot: "bg-indigo-400", text: "text-indigo-200", ring: "ring-indigo-300", plus: "#a5b4fc" },
    { dot: "bg-rose-400", text: "text-rose-200", ring: "ring-rose-300", plus: "#fda4af" },
  ];
  const TRUCO_SHORT = ["", "T", "RT", "V4"];
  const MARK = { sung: "?", accepted: "✓", rejected: "✕" };
  const MARK_TONE = {
    none: "text-amber-100/35",
    sung: "text-amber-300 sung",
    accepted: "text-emerald-300",
    rejected: "text-red-300",
  };
</script>

{#snippet marker(
  kind: "envido" | "truco",
  label: string,
  state: "none" | "sung" | "accepted" | "rejected",
  detail: string,
)}
  <span
    class="inline-flex items-center gap-1 font-mono text-xs font-bold {MARK_TONE[state]}"
    title={detail}
    data-testid="marker-{kind}"
    data-state={state}
  >
    <span>{label}</span>
    <span class="inline-block w-3 text-center">{state === "none" ? "–" : MARK[state]}</span>
  </span>
{/snippet}

<div class="plaque flex w-60 flex-col gap-2 rounded-2xl p-3 text-amber-50" data-testid="scoreboard">
  {#each [0, 1] as team (team)}
    {@const score = view.score[team]}
    {@const players = view.seats.filter((s) => s.team === team)}
    <div
      class="group relative rounded-xl px-2 py-1.5 {myTeam === team
        ? 'bg-white/10 ring-1 ring-amber-200/30'
        : ''}"
      role="group"
      aria-label={view.team_names[team]}
    >
      <div class="flex items-center gap-2">
        <span class="h-2.5 w-2.5 shrink-0 rounded-full {TEAM[team].dot}"></span>
        <p class="min-w-0 flex-1 truncate text-sm font-bold">{view.team_names[team]}</p>
        <!-- rondas won this mano, fighting-game style -->
        <span class="flex gap-1" aria-label={t("game.rondas")}>
          {#each mano.rondas as r, i (i)}
            <span
              class="h-2 w-2 rotate-45 {r === team
                ? TEAM[team].dot
                : r === 'parda'
                  ? 'bg-slate-300/80'
                  : 'border border-amber-100/30'}"
              data-ronda={r === null
                ? "open"
                : r === team
                  ? "won"
                  : r === "parda"
                    ? "parda"
                    : "lost"}
            ></span>
          {/each}
        </span>
        <span class="relative">
          <span class="font-mono text-2xl font-black tabular-nums" data-testid="score-{team}"
            >{Math.round(shown[team].current)}</span
          >
          {#key gained[team].id}
            {#if gained[team].points}
              <span
                class="gain pointer-events-none absolute -top-3 left-full ml-1 font-mono text-lg font-black"
                style="color: {TEAM[team].plus}"
                data-testid="gain-{team}">+{gained[team].points}</span
              >
            {/if}
          {/key}
        </span>
      </div>
      <div class="mt-1 flex items-center gap-1 pl-4" aria-hidden="true">
        {#each tally(score, view.target) as count, i (i)}
          {#if i > 0 && i === Math.ceil(view.malas_max / 5)}<span
              class="mx-0.5 h-5 w-px bg-amber-100/30"
            ></span>{/if}
          <span class="relative h-[18px] w-[18px] rounded-sm ring-1 ring-amber-100/10">
            {#each SIDES.slice(0, count) as side, j (j)}
              <img
                src={FOSFORO}
                alt=""
                class="fosforo absolute h-[18px] w-[3px]"
                style="{side}; --d: {j * 60}ms"
              />
            {/each}
          </span>
        {/each}
        <span
          class="ml-auto text-[0.6rem] tracking-wide whitespace-nowrap {TEAM[team].text} uppercase"
        >
          {#if myTeam === team}<span>{t("game.yourTeam")}</span> ·
          {/if}{score > view.malas_max ? "buenas" : "malas"}
        </span>
      </div>

      <!-- who plays for this team -->
      <div
        class="pointer-events-none absolute top-0 left-full z-40 ml-3 hidden w-56 rounded-xl bg-white p-2 text-slate-900 shadow-xl group-hover:block"
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

  <!-- the mano: which one, and how the envido and truco stand -->
  <div class="flex items-center gap-3 border-t border-amber-100/15 px-2 pt-2 text-[0.65rem]">
    {#if view.hand_kind}
      <span class="font-semibold text-amber-100/70">
        {t("game.handNumber", { n: view.hand_number })}{view.hand_kind === "pica_pica"
          ? " · pica-pica"
          : ""}
      </span>
    {/if}
    <span class="ml-auto flex gap-3">
      {@render marker(
        "envido",
        "E",
        mano.envido?.state ?? "none",
        mano.envido
          ? `${mano.envido.label}: ${t(`game.${mano.envido.state}`)}${"points" in mano.envido && mano.envido.points ? ` (${mano.envido.tanto != null ? `${mano.envido.tanto}, ` : ""}+${mano.envido.points})` : ""}`
          : "Envido",
      )}
      {@render marker(
        "truco",
        TRUCO_SHORT[view.truco_level] || "T",
        mano.truco?.state ?? "none",
        mano.truco ? `${mano.truco.label}: ${t(`game.${mano.truco.state}`)}` : "Truco",
      )}
    </span>
  </div>
</div>

<style>
  /* Dark wood and brass, see-through so the room shows behind it. */
  .plaque {
    background: linear-gradient(160deg, rgb(74 44 23 / 0.62), rgb(30 17 8 / 0.55));
    border: 1px solid rgb(234 179 8 / 0.3);
    box-shadow: 0 10px 30px rgb(0 0 0 / 0.35);
    backdrop-filter: blur(3px);
  }
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
  .gain {
    text-shadow: 0 1px 6px rgb(0 0 0 / 0.6);
    animation: gain 1.4s ease-out both;
  }
  @keyframes gain {
    0% {
      opacity: 0;
      transform: translateY(8px) scale(0.6);
    }
    15%,
    60% {
      opacity: 1;
      transform: translateY(0) scale(1.15);
    }
    100% {
      opacity: 0;
      transform: translateY(-10px) scale(1);
    }
  }
  .sung {
    animation: blink 1s ease-in-out infinite;
  }
  @keyframes blink {
    50% {
      opacity: 0.4;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .fosforo,
    .gain,
    .sung {
      animation: none !important;
    }
  }
</style>
