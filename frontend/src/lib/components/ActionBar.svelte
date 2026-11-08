<script lang="ts">
  import type { Snippet } from "svelte";
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
    /** The viewer's real tanto, offered first when declaring. */
    tanto?: number | null;
  }

  let { actions, onAct, tanto = null }: Props = $props();

  // Keys are not shown on the buttons ("how to play" lists them), only told to screen readers.
  const keys = $derived(bindings());

  const ANSWERS = new Set(["quiero", "no_quiero", "son_buenas", "aceptar_perdon"]);
  const buttons = $derived(buttonActions(actions));
  const declarations = $derived(actions.filter((a) => a.kind === "declarar"));
  // While declaring, Son buenas sits with the numbers.
  const answers = $derived(
    buttons.filter((a) => ANSWERS.has(a.kind) && !(declarations.length && a.kind === "son_buenas")),
  );
  const cantos = $derived(buttons.filter((a) => LOUD.has(a.kind)));
  const others = $derived(buttons.filter((a) => !ANSWERS.has(a.kind) && !LOUD.has(a.kind)));
  const strictSenas = $derived(actions.filter((a) => a.kind === "sena"));

  // Declaring: the real tanto first, then Son buenas; any other number (a farol, open to
  // reclamo, 11.8) is one click away.
  const real = $derived(declarations.find((d) => d.number === tanto));
  const sonBuenas = $derived(actions.find((a) => a.kind === "son_buenas"));
  const otherNumbers = $derived(declarations.filter((d) => d !== real));
  let showOthers = $state(false);
  $effect(() => {
    if (!declarations.length) showOthers = false;
  });
</script>

{#snippet chip(a: GameAction, tone: string)}
  <button
    class="chip inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-bold whitespace-nowrap shadow-md transition hover:-translate-y-0.5 {tone}"
    aria-label={actionLabel(a)}
    aria-keyshortcuts={keyHint(a.kind, keys) ?? undefined}
    onclick={() => onAct(a)}
  >
    {actionLabel(a)}
  </button>
{/snippet}

<!-- A menu that opens upwards on hover (or keyboard focus): the table stays uncluttered. -->
{#snippet menu(label: string, tone: string, body: Snippet)}
  <div class="group relative">
    <button
      type="button"
      class="inline-flex items-center gap-1 rounded-full px-3.5 py-1.5 text-sm font-bold shadow-md {tone}"
      aria-haspopup="true"
    >
      {label}<span class="text-xs opacity-70" aria-hidden="true">▴</span>
    </button>
    <div
      class="absolute right-0 bottom-full z-40 hidden pb-2 group-focus-within:block group-hover:block"
    >
      {@render body()}
    </div>
  </div>
{/snippet}

<div class="flex flex-col items-end gap-2" data-testid="actions">
  {#if declarations.length}
    <div
      class="flex flex-col items-end gap-2 rounded-xl bg-slate-950/75 p-2 shadow-xl"
      role="group"
      aria-label={t("game.declare")}
      data-testid="declare"
    >
      {#if tanto !== null}
        <span class="text-xs font-semibold text-amber-200">{t("game.yourTanto", { n: tanto })}</span
        >
      {/if}
      <div class="flex flex-wrap justify-end gap-2">
        {#if real}
          <button
            class="chip rounded-full bg-emerald-500 px-4 py-1.5 text-base font-extrabold text-white shadow-md ring-2 ring-emerald-200 transition hover:-translate-y-0.5"
            onclick={() => onAct(real)}>{t("game.declareN", { n: real.number ?? 0 })}</button
          >
        {/if}
        {#if sonBuenas}{@render chip(sonBuenas, "bg-slate-200 text-slate-900")}{/if}
        {#if otherNumbers.length && real}
          <button
            type="button"
            class="rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white/85 hover:bg-white/25"
            aria-expanded={showOthers}
            onclick={() => (showOthers = !showOthers)}>{t("game.otherNumber")}</button
          >
        {/if}
      </div>
      {#if showOthers || !real}
        <div class="flex max-w-80 flex-wrap justify-end gap-1">
          {#each otherNumbers as a (a.number)}
            <button
              type="button"
              class="rounded-md bg-white/90 px-2 py-0.5 text-sm font-bold hover:bg-amber-200"
              onclick={() => onAct(a)}>{a.number}</button
            >
          {/each}
        </div>
      {/if}
    </div>
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
  <div class="flex items-end gap-2">
    {#if others.length || strictSenas.length}
      {#snippet more()}
        <div
          class="flex flex-col items-end gap-1.5 rounded-xl bg-slate-950/80 p-2 shadow-xl"
          role="group"
          aria-label={t("game.other")}
        >
          {#each others as a (a.kind)}
            {@render chip(
              a,
              LEAVE.has(a.kind)
                ? "bg-white/90 text-red-800 text-xs"
                : "bg-white/90 text-slate-800 text-xs",
            )}
          {/each}
          {#if strictSenas.length}
            <select
              class="rounded-full border-0 bg-white/90 px-3 py-1 text-xs font-semibold"
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
      {/snippet}
      {@render menu(t("game.other"), "bg-white/85 text-slate-800", more)}
    {/if}
    {#if cantos.length}
      {#snippet sing()}
        <div
          class="flex flex-col items-end gap-1.5 rounded-xl bg-slate-950/80 p-2 shadow-xl"
          role="group"
          aria-label={t("game.cantos")}
        >
          {#each cantos as a (a.kind)}
            {@render chip(a, "bg-amber-400 text-amber-950 ring-2 ring-amber-200")}
          {/each}
        </div>
      {/snippet}
      {@render menu(t("game.cantos"), "bg-amber-400 text-amber-950 ring-2 ring-amber-200", sing)}
    {/if}
  </div>
</div>
