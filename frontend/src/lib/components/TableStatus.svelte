<script lang="ts">
  import type { GameView } from "$lib/api/client";
  import { status } from "$lib/game";
  import { t } from "$lib/i18n.svelte";

  let { view }: { view: GameView } = $props();

  const table = $derived(status(view));
  const TEAM_BG = ["bg-indigo-500 ring-indigo-200", "bg-rose-500 ring-rose-200"];
  const STATE_ICON = { sung: "♪", accepted: "✓", rejected: "✗" };
  const STATE_TONE = {
    sung: "bg-amber-400 text-amber-950",
    accepted: "bg-emerald-500 text-white",
    rejected: "bg-slate-500 text-white",
  };
</script>

<div
  class="plaque flex flex-col gap-1.5 rounded-xl px-3 py-2 text-xs text-amber-50 shadow-xl"
  data-testid="status"
>
  <div class="flex items-center gap-2">
    <span class="font-semibold tracking-wide text-amber-200/90 uppercase">{t("game.rondas")}</span>
    {#each table.rondas as r, i (i)}
      <span
        class="inline-flex h-6 w-6 items-center justify-center rounded-full text-[0.7rem] font-black ring-2 transition {r ===
        null
          ? 'border border-dashed border-amber-100/50 text-amber-100/60 ring-transparent'
          : r === 'parda'
            ? 'bg-gradient-to-br from-slate-200 to-slate-400 text-slate-800 ring-slate-100'
            : `${TEAM_BG[r]} text-white`}"
        title={r === null ? "" : r === "parda" ? "parda" : view.team_names[r]}
        data-ronda={r === null ? "open" : r}
      >
        {r === "parda" ? "=" : r === null ? i + 1 : "★"}
      </span>
    {/each}
  </div>
  {#each [table.envido, table.truco] as canto, i (i)}
    {#if canto}
      <div
        class="flex items-center gap-1.5"
        data-testid={i === 0 ? "status-envido" : "status-truco"}
      >
        <span class="font-bold text-amber-200">{canto.label}</span>
        <span class="rounded-full px-1.5 py-px text-[0.65rem] font-bold {STATE_TONE[canto.state]}">
          {STATE_ICON[canto.state]}
          {t(`game.${canto.state}`)}
        </span>
        {#if "points" in canto && canto.points}
          <span class="font-mono font-bold text-amber-100">+{canto.points}</span>
        {/if}
      </div>
    {/if}
  {/each}
</div>

<style>
  .plaque {
    background:
      linear-gradient(180deg, rgb(255 255 255 / 0.08), transparent 40%),
      linear-gradient(135deg, #4a2c17, #2b170b);
    border: 1px solid rgb(234 179 8 / 0.55);
    box-shadow:
      inset 0 0 0 2px rgb(0 0 0 / 0.35),
      0 10px 20px rgb(0 0 0 / 0.35);
  }
</style>
