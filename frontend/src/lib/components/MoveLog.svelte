<script lang="ts">
  import { SENA_NAMES } from "$lib/avatar/avatar";
  import type { GameEvent, GameView } from "$lib/api/client";
  import { LOUD } from "$lib/animation";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";

  interface Props {
    view: GameView;
    /** The event's text, without who did it (the avatar says that). */
    text: (e: GameEvent) => string;
  }

  let { view, text }: Props = $props();

  const RING = ["ring-indigo-400", "ring-rose-400"];
  const events = $derived([...view.events].reverse());
</script>

<aside class="card flex max-h-[44rem] flex-col gap-3 overflow-y-auto text-sm">
  <h2 class="font-semibold">{t("game.moves")}</h2>
  <ol class="space-y-1" data-testid="events">
    {#each events as e, i (i)}
      {#if e.kind === "reparto"}
        <li class="flex items-center gap-2 pt-2 text-xs font-semibold text-slate-400 uppercase">
          <span class="h-px flex-1 bg-slate-200"></span>{text(e)}<span
            class="h-px flex-1 bg-slate-200"
          ></span>
        </li>
      {:else}
        {@const seat = e.seat != null ? view.seats[e.seat] : null}
        <li
          class="flex items-center gap-2 {e.kind === 'fin_mano'
            ? 'text-slate-500'
            : e.kind === 'ronda' || e.kind === 'envido_resuelto'
              ? 'font-semibold'
              : LOUD.has(e.kind)
                ? 'font-semibold text-amber-700'
                : ''}"
        >
          {#if seat}
            <span class="shrink-0 rounded-full ring-2 {RING[seat.team]}" title={seat.name}>
              <Avatar character={seat.character} label={seat.name} class="w-7" />
            </span>
          {:else}
            <span class="w-7 shrink-0 text-center text-slate-400">•</span>
          {/if}
          <span>{text(e)}</span>
        </li>
      {/if}
    {/each}
  </ol>
  {#if view.senas_seen.length}
    <h2 class="font-semibold">{t("game.senasSeen")}</h2>
    <ul>
      {#each view.senas_seen as s, i (i)}
        <li>{view.seats[s.seat].name}: {SENA_NAMES[s.sena]}</li>
      {/each}
    </ul>
  {/if}
</aside>
