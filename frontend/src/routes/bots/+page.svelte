<script lang="ts">
  import { onMount } from "svelte";
  import {
    api,
    errorMessage,
    type BotConfig,
    type BotPreset,
    type BotSettings,
  } from "$lib/api/client";
  import BotConfigurator from "$lib/components/BotConfigurator.svelte";
  import { t } from "$lib/i18n.svelte";

  let presets = $state<BotPreset[]>([]);
  let saved = $state<BotConfig[]>([]);
  let error = $state<string | null>(null);

  async function loadSaved() {
    const { data, response } = await api.GET("/api/bots");
    if (data) saved = data;
    else error = `${response.status} ${response.statusText}`;
  }

  onMount(async () => {
    const { data, response } = await api.GET("/api/bots/presets");
    if (data) presets = data;
    else error = `${response.status} ${response.statusText}`;
    await loadSaved();
  });

  async function save(name: string, settings: BotSettings): Promise<string | null> {
    const res = await api.POST("/api/bots", { body: { name, settings } });
    if (res.error) return errorMessage(res.error);
    await loadSaved();
    return null;
  }

  async function remove(id: number) {
    const res = await api.DELETE("/api/bots/{bot_id}", { params: { path: { bot_id: id } } });
    if (res.error) error = errorMessage(res.error);
    await loadSaved();
  }
</script>

<section class="card space-y-4">
  <div>
    <h1 class="text-xl font-semibold">{t("bots.title")}</h1>
    <p class="mt-1 text-sm text-slate-600">{t("bots.intro")}</p>
  </div>
  {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
  {#if presets.length}
    <BotConfigurator {presets} {saved} onSave={save} />
  {/if}
</section>

<section class="card mt-6">
  <h2 class="mb-3 text-lg font-semibold">{t("bots.saved")}</h2>
  {#if saved.length}
    <ul class="divide-y divide-slate-100">
      {#each saved as bot (bot.id)}
        <li class="flex items-center justify-between py-2 text-sm">
          <span>{bot.name}</span>
          <button class="btn btn-danger" onclick={() => remove(bot.id)}>{t("bots.delete")}</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="text-sm text-slate-600">{t("bots.noSaved")}</p>
  {/if}
</section>
