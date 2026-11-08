<script lang="ts">
  import { SENA_NAMES } from "$lib/avatar/avatar";
  import type { GameAction } from "$lib/api/client";
  import { LEAVE, LOUD } from "$lib/animation";
  import { actionLabel, buttonActions } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import { keyHint } from "$lib/keys";
  import { bindings } from "$lib/profile.svelte";

  interface Props {
    actions: GameAction[];
    onAct: (action: GameAction) => void;
  }

  let { actions, onAct }: Props = $props();

  const keys = $derived(bindings());
  const ANSWERS = new Set(["quiero", "no_quiero", "son_buenas", "aceptar_perdon"]);
  const buttons = $derived(buttonActions(actions));
  const answers = $derived(buttons.filter((a) => ANSWERS.has(a.kind)));
  const cantos = $derived(buttons.filter((a) => LOUD.has(a.kind)));
  const others = $derived(buttons.filter((a) => !ANSWERS.has(a.kind) && !LOUD.has(a.kind)));
  const declarations = $derived(actions.filter((a) => a.kind === "declarar"));
  const strictSenas = $derived(actions.filter((a) => a.kind === "sena"));

  // Declaring: type the number (digits + Enter) or click it.
  let typed = $state("");
  function declareTyped(event: SubmitEvent) {
    event.preventDefault();
    const a = declarations.find((d) => String(d.number) === typed.trim());
    if (a) onAct(a);
    typed = "";
  }
</script>

{#snippet chip(a: GameAction, tone: string)}
  {@const key = keyHint(a.kind, keys)}
  <button
    class="chip inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-bold shadow-md transition hover:-translate-y-0.5 {tone}"
    aria-label={actionLabel(a)}
    aria-keyshortcuts={key ?? undefined}
    onclick={() => onAct(a)}
  >
    {actionLabel(a)}
    {#if key}<kbd class="rounded bg-black/20 px-1 text-[0.65rem] font-bold" aria-hidden="true"
        >{key}</kbd
      >{/if}
  </button>
{/snippet}

<div class="flex flex-col items-end gap-2" data-testid="actions">
  {#if declarations.length}
    <form
      class="flex flex-wrap items-center justify-end gap-1 rounded-xl bg-slate-950/70 p-2"
      onsubmit={declareTyped}
    >
      <span class="mr-1 text-xs font-semibold text-amber-200">{t("game.declare")}</span>
      <input
        class="w-14 rounded-md border-0 bg-white/90 px-2 py-1 text-center text-sm font-bold"
        inputmode="numeric"
        aria-label={t("game.declare")}
        bind:value={typed}
      />
      <div class="flex max-w-80 flex-wrap justify-end gap-1">
        {#each declarations as a (a.number)}
          <button
            type="button"
            class="rounded-md bg-white/90 px-2 py-0.5 text-sm font-bold hover:bg-amber-200"
            onclick={() => onAct(a)}>{a.number}</button
          >
        {/each}
      </div>
    </form>
  {/if}
  {#if answers.length}
    <div class="flex flex-wrap justify-end gap-2" role="group" aria-label={t("game.answers")}>
      {#each answers as a (a.kind)}
        {@render chip(
          a,
          a.kind === "no_quiero"
            ? "bg-slate-200 text-slate-900"
            : "bg-emerald-500 text-white ring-2 ring-emerald-200",
        )}
      {/each}
    </div>
  {/if}
  {#if cantos.length}
    <div class="flex flex-wrap justify-end gap-2" role="group" aria-label={t("game.cantos")}>
      {#each cantos as a (a.kind)}
        {@render chip(a, "bg-amber-400 text-amber-950 ring-2 ring-amber-200")}
      {/each}
    </div>
  {/if}
  {#if others.length}
    <div class="flex flex-wrap justify-end gap-1.5" role="group" aria-label={t("game.other")}>
      {#each others as a (a.kind)}
        {@render chip(
          a,
          LEAVE.has(a.kind)
            ? "bg-white/85 text-red-800 text-xs"
            : "bg-white/85 text-slate-800 text-xs",
        )}
      {/each}
    </div>
  {/if}
  {#if strictSenas.length}
    <select
      class="rounded-full border-0 bg-white/85 px-3 py-1 text-xs font-semibold"
      aria-label={t("game.senaPick")}
      onchange={(e) => {
        const a = strictSenas.find((s) => s.sena === e.currentTarget.value);
        if (a) onAct(a);
        e.currentTarget.value = "";
      }}
    >
      <option value="">{t("game.senaPick")}</option>
      {#each strictSenas as a (a.sena)}
        <option value={a.sena}>{a.sena ? SENA_NAMES[a.sena] : ""}</option>
      {/each}
    </select>
  {/if}
</div>
