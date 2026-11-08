<script lang="ts">
  import { SENA_NAMES } from "$lib/avatar/avatar";
  import type { GameEvent, GameView } from "$lib/api/client";
  import { LEAVE, LOUD } from "$lib/animation";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";

  interface Props {
    view: GameView;
    /** The event's text, without who did it (the avatar says that). */
    text: (e: GameEvent) => string;
  }

  let { view, text }: Props = $props();

  const RING = ["ring-indigo-400", "ring-rose-400"];
  const TEAM_TEXT = ["text-indigo-300", "text-rose-300"];
  // Newest first. Keys are the event's place in the whole log, so only new rows animate in.
  const events = $derived(view.events.map((e, n) => ({ e, n })).reverse());
  const teamOf = (e: GameEvent) => (e.seat != null ? view.seats[e.seat].team : null);

  /** How a plain move reads: answers, cantos and the mazo each have their tone. */
  function tone(kind: string): string {
    if (LOUD.has(kind)) return "canto";
    if (kind === "quiero" || kind === "son_buenas" || kind === "aceptar_perdon") return "yes";
    if (kind === "no_quiero" || LEAVE.has(kind)) return "no";
    if (kind === "interferencia" || kind === "reclamar" || kind === "objetar") return "claim";
    return "";
  }
</script>

{#snippet who(e: GameEvent)}
  {@const seat = e.seat != null ? view.seats[e.seat] : null}
  {#if seat}
    <span class="shrink-0 rounded-full ring-2 {RING[seat.team]}" title={seat.name}>
      <Avatar character={seat.character} label={seat.name} class="w-7" />
    </span>
  {:else}
    <span class="w-7 shrink-0 text-center text-amber-100/40">•</span>
  {/if}
{/snippet}

<aside
  class="log flex max-h-full flex-col gap-3 overflow-y-auto rounded-2xl p-3 text-sm text-amber-50"
  aria-label={t("game.moves")}
>
  <h2 class="font-semibold text-amber-200">{t("game.moves")}</h2>
  <ol class="space-y-1.5" data-testid="events">
    {#each events as { e, n } (n)}
      {@const team = teamOf(e)}
      {#if e.kind === "reparto"}
        <li
          class="entry flex items-center gap-2 pt-2 text-xs font-semibold text-amber-100/50 uppercase"
          data-kind={e.kind}
        >
          <span class="h-px flex-1 bg-amber-100/20"></span>{text(e)}<span
            class="h-px flex-1 bg-amber-100/20"
          ></span>
        </li>
      {:else if e.kind === "ronda"}
        <!-- a ronda: a pill in the winning team's colour, silver for a parda -->
        <li
          class="entry flex items-center gap-2 rounded-full py-0.5 pr-3 pl-0.5 font-semibold {team ===
          null
            ? 'bg-slate-300/20 text-slate-100'
            : team === 0
              ? 'bg-indigo-500/30 text-indigo-50'
              : 'bg-rose-500/30 text-rose-50'}"
          data-kind={e.kind}
        >
          {@render who(e)}
          <span class="flex-1">{text(e)}</span>
          <span aria-hidden="true">{team === null ? "=" : "★"}</span>
        </li>
      {:else if e.kind === "envido_resuelto"}
        <!-- the envido: a gold card with the points won -->
        <li
          class="entry gold flex items-center gap-2 rounded-xl px-1.5 py-1 font-semibold text-amber-950"
          data-kind={e.kind}
        >
          {@render who(e)}
          <span class="flex-1"
            >Envido{#if e.number != null}<span class="ml-1.5 font-mono font-black">{e.number}</span
              >{:else if e.seat == null}<span class="ml-1.5 text-xs"
                >{view.team_names[(e.points?.[1] ?? 0) > (e.points?.[0] ?? 0) ? 1 : 0]}</span
              >{/if}</span
          >
          <span class="font-mono text-base font-black">+{Math.max(...(e.points ?? [0]))}</span>
        </li>
      {:else if e.kind === "fin_mano"}
        <!-- the end of a mano: what each team scored -->
        <li
          class="entry flex items-center justify-between gap-2 rounded-xl border border-amber-200/25 bg-black/20 px-3 py-1.5 text-xs"
          data-kind={e.kind}
        >
          <span class="font-semibold tracking-wide text-amber-200/80 uppercase"
            >{t("game.manoEnd")}</span
          >
          <span class="flex gap-3 font-mono font-black">
            {#each [0, 1] as tm (tm)}
              <span class={TEAM_TEXT[tm]} title={view.team_names[tm]}>+{e.points?.[tm] ?? 0}</span>
            {/each}
          </span>
        </li>
      {:else if e.kind === "resultado"}
        <!-- the end of the match -->
        <li
          class="entry gold flex items-center gap-2 rounded-xl px-3 py-2 text-base font-black text-amber-950"
          data-kind={e.kind}
        >
          <span aria-hidden="true">🏆</span>
          <span class="flex-1">
            {view.result?.winner != null
              ? t("game.won", { team: view.team_names[view.result.winner] })
              : t("game.noWinner")}
          </span>
          <span class="font-mono">{text(e)}</span>
        </li>
      {:else}
        {@const kind = tone(e.kind)}
        <li class="entry flex items-center gap-2" data-kind={e.kind} data-tone={kind || undefined}>
          {@render who(e)}
          <span
            class={kind === "canto"
              ? "text-base font-black tracking-wide text-amber-300 uppercase"
              : kind === "yes"
                ? "font-semibold text-emerald-300"
                : kind === "no"
                  ? "font-semibold text-red-300"
                  : kind === "claim"
                    ? "text-amber-100/70 italic"
                    : ""}>{kind === "canto" ? `¡${text(e)}!` : text(e)}</span
          >
        </li>
      {/if}
    {/each}
  </ol>
  {#if view.senas_seen.length}
    <h2 class="font-semibold text-amber-200">{t("game.senasSeen")}</h2>
    <ul>
      {#each view.senas_seen as s, i (i)}
        <li>{view.seats[s.seat].name}: {SENA_NAMES[s.sena]}</li>
      {/each}
    </ul>
  {/if}
</aside>

<style>
  .log {
    background: linear-gradient(160deg, rgb(74 44 23 / 0.8), rgb(30 17 8 / 0.78));
    border: 1px solid rgb(234 179 8 / 0.3);
    box-shadow: 0 10px 30px rgb(0 0 0 / 0.4);
    backdrop-filter: blur(4px);
  }
  .gold {
    background: linear-gradient(135deg, #fde68a, #f59e0b 60%, #d97706);
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / 0.5),
      0 2px 8px rgb(0 0 0 / 0.3);
  }
  /* A new move slides in at the top. */
  .entry {
    animation: enter 0.35s ease-out both;
  }
  @keyframes enter {
    from {
      opacity: 0;
      transform: translateY(-6px);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .entry {
      animation: none;
    }
  }
</style>
