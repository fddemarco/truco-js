<script lang="ts">
  import type { SeatView } from "$lib/api/client";
  import type { BodySpot, Sena } from "$lib/avatar/avatar";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";

  interface Props {
    seat: SeatView;
    /** What to call this player ("Vos" for the viewer). */
    label: string;
    /** focus: face to face (or the viewer). dim: anyone else, smaller and see-through. */
    look: "focus" | "dim";
    size: "lg" | "md" | "sm";
    /** The viewer's team: a thicker ring. */
    mine: boolean;
    role?: "mano" | "pie" | null;
    turn?: boolean;
    acting?: boolean;
    sena?: { sena: Sena; spot: BodySpot };
    onclick?: () => void;
  }

  let {
    seat,
    label,
    look,
    size,
    mine,
    role = null,
    turn = false,
    acting = false,
    sena,
    onclick,
  }: Props = $props();

  const SIZES = { lg: "w-28", md: "w-20", sm: "w-16" };
  // Team colors: indigo for team 0, rose for team 1 (as on the scoreboard).
  const RING = ["ring-indigo-400", "ring-rose-400"];
  const out = $derived(seat.in_play && !seat.active);
</script>

{#snippet icon(kind: "mano" | "pie")}
  <span
    class="absolute -right-1 -bottom-1 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-slate-100 to-slate-400 text-slate-700 shadow ring-1 ring-white/70"
    title={t(kind === "mano" ? "game.roleMano" : "game.rolePie")}
    data-testid="role-{kind}"
  >
    {#if kind === "mano"}
      <svg
        viewBox="0 0 24 24"
        class="h-4 w-4"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M18 11V6a2 2 0 0 0-4 0" />
        <path d="M14 10V4a2 2 0 0 0-4 0v2" />
        <path d="M10 10.5V6a2 2 0 0 0-4 0v8" />
        <path
          d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-6-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"
        />
      </svg>
    {:else}
      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="currentColor" aria-hidden="true">
        <path
          d="M9.5 22c-2.6 0-3.8-2.1-3.6-4.6.2-2.6 1.5-4.4 1.6-6.6.1-1.9 1.2-3.3 3-3.3 2.1 0 3.2 1.7 3 4.1-.2 2.5-1.3 4.6-1.3 6.8 0 2.2-.4 3.6-2.7 3.6z"
        />
        <circle cx="8" cy="4.6" r="1.6" />
        <circle cx="11.2" cy="3.6" r="1.3" />
        <circle cx="13.8" cy="4.4" r="1.1" />
        <circle cx="15.6" cy="6" r="0.9" />
        <circle cx="16.6" cy="8" r="0.8" />
      </svg>
    {/if}
  </span>
{/snippet}

<div
  class="seat relative flex flex-col items-center gap-1 transition duration-300"
  data-look={look}
  data-testid="badge-{seat.seat}"
>
  <button
    type="button"
    class="relative rounded-full p-1 ring-offset-2 ring-offset-transparent {RING[seat.team]} {mine
      ? 'ring-4'
      : 'ring-2'} {role === 'mano'
      ? 'outline-double outline-4 outline-offset-2 outline-slate-300'
      : role === 'pie'
        ? 'outline-dashed outline-2 outline-offset-4 outline-slate-300'
        : ''} {acting ? 'acting' : turn ? 'turn' : ''} {out ? 'opacity-40 grayscale' : ''}"
    aria-label={label}
    title="{label} · {t('game.number', { n: seat.number })}"
    {onclick}
    disabled={!onclick}
  >
    <div
      class="face overflow-hidden rounded-full bg-gradient-to-b from-slate-200/90 to-slate-400/80"
    >
      <Avatar
        character={seat.character}
        {label}
        sena={sena?.sena}
        spot={sena?.spot}
        class={SIZES[size]}
      />
    </div>
    {#if role}{@render icon(role)}{/if}
  </button>
  <div
    class="flex max-w-36 items-center gap-1 truncate rounded-full bg-slate-950/70 px-2 py-0.5 text-xs font-semibold text-white shadow"
  >
    <span class="h-2 w-2 shrink-0 rounded-full {seat.team ? 'bg-rose-400' : 'bg-indigo-400'}"
    ></span>
    <span class="truncate">{label}</span>
    {#if out}<span class="text-red-300">· {t("game.toMazo")}</span>{/if}
  </div>
</div>

<style>
  .seat[data-look="dim"] {
    transform: scale(0.88);
    opacity: 0.8;
  }
  .turn {
    box-shadow:
      0 0 0 3px #fbbf24,
      0 0 16px 4px rgba(251, 191, 36, 0.6);
  }
  .acting {
    box-shadow:
      0 0 0 4px #38bdf8,
      0 0 18px 4px rgba(56, 189, 248, 0.7);
  }
</style>
