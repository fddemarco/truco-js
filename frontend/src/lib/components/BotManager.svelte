<script lang="ts">
  import { onMount } from "svelte";
  import { api, errorMessage, type BotConfig, type BotPreset } from "$lib/api/client";
  import { CHARACTER_NAMES, isCharacter } from "$lib/avatar/avatar";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";
  import type { BotDraft } from "$lib/bots";
  import BotConfigurator from "./BotConfigurator.svelte";

  let presets = $state<BotPreset[]>([]);
  let saved = $state<BotConfig[]>([]);
  let error = $state<string | null>(null);
  /** What the editor shows: nothing, a new bot (optionally from a preset), or a saved bot. */
  let editor = $state<{ id: number | null; draft?: BotDraft } | null>(null);

  async function loadSaved() {
    const res = await api.GET("/api/bots");
    if (res.data) saved = res.data;
    else error = errorMessage(res.error);
  }

  onMount(async () => {
    const res = await api.GET("/api/bots/presets");
    if (res.data) presets = res.data;
    else error = errorMessage(res.error);
    await loadSaved();
  });

  async function save(bot: BotDraft): Promise<string | null> {
    const id = editor?.id ?? null;
    const res =
      id === null
        ? await api.POST("/api/bots", { body: bot })
        : await api.PUT("/api/bots/{bot_id}", { params: { path: { bot_id: id } }, body: bot });
    if (res.error) return errorMessage(res.error);
    await loadSaved();
    editor = null;
    return null;
  }

  async function remove(bot: BotConfig) {
    if (!confirm(t("bots.confirmDelete", { name: bot.name }))) return;
    const res = await api.DELETE("/api/bots/{bot_id}", { params: { path: { bot_id: bot.id } } });
    if (res.error) error = errorMessage(res.error);
    await loadSaved();
  }

  function duplicate(p: BotPreset) {
    editor = {
      id: null,
      draft: { name: t("bots.copyOf", { name: p.name }), character: null, settings: p.settings },
    };
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <p class="text-sm text-slate-600">{t("bots.intro")}</p>
    {#if !editor}
      <button class="btn btn-primary shrink-0" onclick={() => (editor = { id: null })}>
        + {t("bots.new")}
      </button>
    {/if}
  </div>
  {#if error}<p class="text-sm text-red-600" role="alert">{error}</p>{/if}

  {#if editor && presets.length}
    <section class="rounded-xl border-2 border-indigo-200 bg-indigo-50/40 p-4">
      <h2 class="mb-3 font-semibold">
        {editor.id === null ? t("bots.new") : t("bots.edit", { name: editor.draft?.name ?? "" })}
      </h2>
      {#key editor}
        <BotConfigurator
          {presets}
          {saved}
          editing={editor.draft}
          onSave={save}
          onCancel={() => (editor = null)}
        />
      {/key}
    </section>
  {/if}

  <section>
    <h2 class="mb-2 font-semibold">{t("bots.saved")}</h2>
    {#if saved.length}
      <ul class="grid gap-3 sm:grid-cols-2">
        {#each saved as bot (bot.id)}
          <li class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
            {#if isCharacter(bot.character)}
              <Avatar
                character={bot.character}
                label={CHARACTER_NAMES[bot.character]}
                class="w-14"
              />
            {:else}
              <div
                class="flex h-14 w-14 items-center justify-center rounded-full bg-slate-200 text-xl"
                aria-hidden="true"
              >
                ?
              </div>
            {/if}
            <span class="flex-1 font-semibold">{bot.name}</span>
            <button
              class="btn"
              onclick={() =>
                (editor = {
                  id: bot.id,
                  draft: { name: bot.name, character: bot.character, settings: bot.settings },
                })}>{t("bots.editShort")}</button
            >
            <button class="btn btn-danger" onclick={() => remove(bot)}>{t("bots.delete")}</button>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="text-sm text-slate-600">{t("bots.noSaved")}</p>
    {/if}
  </section>

  <section>
    <h2 class="mb-2 font-semibold">{t("bots.presets")}</h2>
    <ul class="grid gap-3 sm:grid-cols-2">
      {#each presets as p (p.key)}
        <li class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
          <div class="flex-1">
            <p class="font-semibold">{p.name}</p>
            <p class="text-xs text-slate-600">{t(`bots.preset.${p.key}` as MessageKey)}</p>
          </div>
          <button class="btn" onclick={() => duplicate(p)}>{t("bots.duplicate")}</button>
        </li>
      {/each}
    </ul>
  </section>
</div>
