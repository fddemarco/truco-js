<script lang="ts">
  import type { ChainSetup, ScoringInfo } from "$lib/api/client";
  import { t } from "$lib/i18n.svelte";
  import {
    CANTO_LABELS,
    chainKey,
    chainLabel,
    DEFAULT_TARGET,
    defaults,
    FAMILIES,
    findChain,
    MAX_POINTS,
    MAX_TARGET,
    MIN_TARGET,
    nextCantos,
    removeChain,
    setChain,
    type Family,
    type ScoringPrefs,
  } from "$lib/scoring";

  interface Props {
    /** The chains that can be sung, with the reglamento's points (GET /api/games/scoring). */
    info: ScoringInfo;
    value: ScoringPrefs;
    onChange: (value: ScoringPrefs) => void;
  }
  let { info, value, onChange }: Props = $props();

  const TARGETS = [15, 18, 24, 30, 40];

  /** The chain being built in each family, one canto at a time. */
  let building = $state<Record<Family, string[] | null>>({ envido: null, truco: null });

  const defined = $derived(new Set(value.chains.map((c) => chainKey(c.chain))));
  const rowsOf = (family: Family) =>
    value.chains.filter((c) => findChain(info, c.chain)?.family === family);

  function setTarget(n: number) {
    if (!Number.isFinite(n)) return;
    const target = Math.min(MAX_TARGET, Math.max(MIN_TARGET, Math.round(n)));
    onChange({ ...value, target });
  }

  function setPoints(chain: string[], field: "quiero" | "no_quiero", raw: string) {
    const n = raw === "" ? null : Math.min(MAX_POINTS, Math.max(0, Math.round(Number(raw))));
    if (n !== null && !Number.isFinite(n)) return;
    onChange({ ...value, chains: setChain(value.chains, chain, { [field]: n }) });
  }

  function add(family: Family) {
    const chain = building[family];
    if (!chain?.length || defined.has(chainKey(chain))) return;
    onChange({ ...value, chains: setChain(value.chains, chain, {}) });
    building[family] = null;
  }

  function remove(chain: ChainSetup["chain"]) {
    onChange({ ...value, chains: removeChain(value.chains, chain) });
  }
</script>

{#snippet chips(chain: readonly string[])}
  <span class="flex flex-wrap items-center gap-1">
    {#each chain as c, i (i)}
      {#if i > 0}<span class="text-amber-300/70" aria-hidden="true">→</span>{/if}
      <span
        class="rounded-full bg-amber-400/15 px-2 py-0.5 text-xs font-bold text-amber-100 ring-1 ring-amber-300/30"
        >{CANTO_LABELS[c] ?? c}</span
      >
    {/each}
  </span>
{/snippet}

<div class="space-y-6">
  <!-- the partido length -->
  <section class="felt-inset rounded-xl p-4">
    <div class="flex flex-wrap items-center gap-3">
      <label for="target" class="font-bold text-amber-50">{t("scoring.target")}</label>
      <div class="flex items-center overflow-hidden rounded-lg ring-1 ring-amber-200/30">
        <button
          type="button"
          class="bg-black/30 px-3 py-1.5 font-bold hover:bg-black/50 disabled:opacity-40"
          aria-label={t("scoring.less")}
          disabled={value.target <= MIN_TARGET}
          onclick={() => setTarget(value.target - 1)}>−</button
        >
        <input
          id="target"
          class="w-16 bg-black/40 py-1.5 text-center font-mono text-lg font-black text-amber-200 [appearance:textfield] focus:outline-none"
          type="number"
          min={MIN_TARGET}
          max={MAX_TARGET}
          value={value.target}
          onchange={(e) => setTarget(Number(e.currentTarget.value))}
        />
        <button
          type="button"
          class="bg-black/30 px-3 py-1.5 font-bold hover:bg-black/50 disabled:opacity-40"
          aria-label={t("scoring.more")}
          disabled={value.target >= MAX_TARGET}
          onclick={() => setTarget(value.target + 1)}>+</button
        >
      </div>
      <span class="text-sm text-amber-100/70">{t("scoring.points")}</span>
      <div class="flex flex-wrap gap-1" role="group" aria-label={t("scoring.quick")}>
        {#each TARGETS as n (n)}
          <button
            type="button"
            class="rounded-full px-2.5 py-0.5 text-xs font-bold ring-1 {value.target === n
              ? 'bg-amber-400 text-amber-950 ring-amber-400'
              : 'ring-amber-200/30 hover:bg-white/10'}"
            aria-pressed={value.target === n}
            onclick={() => setTarget(n)}>{n}</button
          >
        {/each}
      </div>
    </div>
    <p class="mt-2 text-xs text-amber-100/70">
      {t("scoring.targetHint", { malas: Math.floor(value.target / 2), target: value.target })}
      {#if value.target !== DEFAULT_TARGET}<span class="text-amber-300"
          >{t("scoring.notReglamento")}</span
        >{/if}
    </p>
  </section>

  <!-- points per canto chain -->
  <section class="space-y-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="font-bold text-amber-50">{t("scoring.chains")}</h3>
        <p class="max-w-2xl text-xs text-amber-100/70">{t("scoring.intro")}</p>
      </div>
      {#if value.chains.length}
        <button type="button" class="btn" onclick={() => onChange({ ...value, chains: [] })}
          >{t("scoring.reset")}</button
        >
      {/if}
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      {#each FAMILIES as family (family)}
        {@const rows = rowsOf(family)}
        {@const chain = building[family]}
        <div
          class="rounded-xl bg-black/20 p-3 ring-1 ring-amber-200/15"
          data-testid="family-{family}"
        >
          <h4 class="mb-2 text-xs font-black tracking-widest text-amber-300 uppercase">
            {family === "envido" ? "Envido" : "Truco"}
          </h4>

          {#if rows.length}
            <div
              class="mb-2 grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-2 gap-y-1.5 text-sm"
            >
              <span></span>
              <span class="w-16 text-center text-[0.65rem] font-bold text-amber-100/60">Quiero</span
              >
              <span class="w-16 text-center text-[0.65rem] font-bold text-amber-100/60"
                >No quiero</span
              >
              <span></span>
              {#each rows as row (chainKey(row.chain))}
                {@const d = defaults(info, value.chains, row.chain)}
                {@render chips(row.chain)}
                <input
                  class="input w-16 text-center font-mono"
                  type="number"
                  min="0"
                  max={MAX_POINTS}
                  aria-label="{chainLabel(row.chain)}: quiero"
                  placeholder={d.quiero === "falta" ? t("scoring.falta") : String(d.quiero)}
                  title={t("scoring.default", {
                    n: d.quiero === "falta" ? t("scoring.falta") : d.quiero,
                  })}
                  value={row.quiero ?? ""}
                  oninput={(e) => setPoints(row.chain, "quiero", e.currentTarget.value)}
                />
                <input
                  class="input w-16 text-center font-mono"
                  type="number"
                  min="0"
                  max={MAX_POINTS}
                  aria-label="{chainLabel(row.chain)}: no quiero"
                  placeholder={String(d.no_quiero)}
                  title={t("scoring.default", { n: d.no_quiero })}
                  value={row.no_quiero ?? ""}
                  oninput={(e) => setPoints(row.chain, "no_quiero", e.currentTarget.value)}
                />
                <button
                  type="button"
                  class="rounded-full px-2 text-lg leading-none text-amber-100/60 hover:text-rose-300"
                  aria-label="{t('scoring.remove')}: {chainLabel(row.chain)}"
                  onclick={() => remove(row.chain)}>×</button
                >
              {/each}
            </div>
          {/if}

          {#if chain === null}
            <button
              type="button"
              class="w-full rounded-lg border border-dashed border-amber-200/30 px-3 py-1.5 text-sm font-semibold text-amber-100/80 hover:border-amber-300 hover:text-amber-100"
              onclick={() => (building[family] = [])}>+ {t("scoring.add")}</button
            >
          {:else}
            {@const next = nextCantos(info, family, chain)}
            {@const taken = chain.length > 0 && defined.has(chainKey(chain))}
            <div class="space-y-2 rounded-lg bg-black/25 p-2.5" data-testid="builder-{family}">
              <div class="flex min-h-7 flex-wrap items-center gap-2">
                {#if chain.length}
                  {@render chips(chain)}
                  <button
                    type="button"
                    class="text-xs text-amber-100/60 underline hover:text-amber-100"
                    onclick={() => (building[family] = chain.slice(0, -1))}
                    >{t("scoring.undo")}</button
                  >
                {:else}
                  <span class="text-xs text-amber-100/70">{t("scoring.pick")}</span>
                {/if}
              </div>
              {#if next.length}
                <div class="flex flex-wrap items-center gap-1.5">
                  {#if chain.length}<span class="text-xs text-amber-100/60"
                      >{t("scoring.next")}</span
                    >{/if}
                  {#each next as c (c)}
                    <button
                      type="button"
                      class="rounded-full bg-amber-400/10 px-2.5 py-0.5 text-xs font-bold ring-1 ring-amber-300/40 hover:bg-amber-400/25"
                      onclick={() => (building[family] = [...chain, c])}
                      >{chain.length ? "→ " : ""}{CANTO_LABELS[c] ?? c}</button
                    >
                  {/each}
                </div>
              {/if}
              {#if taken}<p class="text-xs text-amber-300" role="status">
                  {t("scoring.defined")}
                </p>{/if}
              <div class="flex gap-2">
                <button
                  type="button"
                  class="btn btn-primary"
                  disabled={!chain.length || taken}
                  onclick={() => add(family)}>{t("scoring.addShort")}</button
                >
                <button type="button" class="btn" onclick={() => (building[family] = null)}
                  >{t("bots.cancel")}</button
                >
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
    <p class="text-xs text-amber-100/60">{t("scoring.kept")}</p>
  </section>
</div>
