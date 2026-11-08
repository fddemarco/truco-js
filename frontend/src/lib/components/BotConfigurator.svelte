<script lang="ts">
  import { untrack } from "svelte";
  import type { BotConfig, BotPreset, BotSettings } from "$lib/api/client";
  import type { Character } from "$lib/avatar/avatar";
  import {
    CARD_ORDERS,
    ENVIDO_CALL_LABELS,
    ENVIDO_CALLS,
    POLICIES,
    RANKS,
    sameSettings,
    type BotDraft,
  } from "$lib/bots";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import CharacterPicker from "./CharacterPicker.svelte";

  interface Props {
    presets: BotPreset[];
    saved: BotConfig[];
    /** The bot being edited. Without it, a new bot starting from a preset or saved bot. */
    editing?: BotDraft;
    /** Save the bot. Resolves to an error message, or null. */
    onSave: (bot: BotDraft) => Promise<string | null>;
    onCancel?: () => void;
  }

  let { presets, saved, editing, onSave, onCancel }: Props = $props();

  type PolicyKey = "envido_sing" | "envido_accept" | "truco_sing" | "truco_accept";
  type TantoKey = "envido_sing_threshold" | "envido_accept_threshold";
  type RankKey = "truco_sing_threshold" | "truco_accept_threshold";

  // Start from the bot being edited, or the first preset; later prop changes don't reset the
  // user's edits.
  const first = untrack(() => editing?.settings ?? presets[0].settings);
  let selection = $state(untrack(() => (editing ? "" : `preset:${presets[0].key}`)));
  const base = $derived.by((): BotSettings => {
    if (!selection) return first;
    const [kind, id] = selection.split(":");
    const found =
      kind === "preset"
        ? presets.find((p) => p.key === id)
        : saved.find((b) => String(b.id) === id);
    return (found ?? presets[0]).settings;
  });
  const description = $derived(
    selection.startsWith("preset:")
      ? t(`bots.preset.${selection.slice(7)}` as MessageKey)
      : undefined,
  );

  let settings = $state<BotSettings>({ ...first });
  const modified = $derived(!editing && !sameSettings(settings, base));

  let name = $state(untrack(() => editing?.name ?? ""));
  let character = $state<Character | null>(untrack(() => editing?.character ?? null));
  let saving = $state(false);
  let message = $state<{ ok: boolean; text: string } | null>(null);

  function select(value: string) {
    selection = value;
    settings = { ...base };
    message = null;
  }

  function toggleRaise(key: "envido_raise_threshold" | "truco_raise_threshold", on: boolean) {
    settings[key] = on ? (key === "envido_raise_threshold" ? 30 : 13) : null;
  }

  async function save(event: SubmitEvent) {
    event.preventDefault();
    saving = true;
    const error = await onSave({
      name: name.trim(),
      character,
      settings: $state.snapshot(settings),
    });
    saving = false;
    message = error ? { ok: false, text: error } : { ok: true, text: t("bots.savedOk") };
    if (!error && !editing) name = "";
  }
</script>

{#snippet policy(key: PolicyKey, label: string)}
  <label class="block text-sm">
    <span class="font-medium">{label}</span>
    <select class="input mt-1" name={key} bind:value={settings[key]}>
      {#each POLICIES as p (p)}
        <option value={p}>{t(`bots.policy.${p}`)}</option>
      {/each}
    </select>
  </label>
{/snippet}

{#snippet tanto(key: TantoKey)}
  <label class="block text-sm">
    <span class="font-medium">{t("bots.threshold")}</span>
    <input
      class="input mt-1"
      type="number"
      min="0"
      max="33"
      name={key}
      bind:value={settings[key]}
    />
    <span class="text-xs text-slate-500">{t("bots.tantoHint")}</span>
  </label>
{/snippet}

{#snippet rank(key: RankKey | "truco_raise_threshold", label: string)}
  <label class="block text-sm">
    <span class="font-medium">{label}</span>
    <select class="input mt-1" name={key} bind:value={settings[key]}>
      {#each RANKS as r (r.rank)}
        <option value={r.rank}>{r.label}</option>
      {/each}
    </select>
    <span class="text-xs text-slate-500">{t("bots.rankHint")}</span>
  </label>
{/snippet}

<div class="space-y-4">
  {#if !editing}
    <label class="block max-w-md text-sm">
      <span class="font-medium">{t("bots.selector")}</span>
      <select
        class="input mt-1"
        name="bot"
        value={selection}
        onchange={(e) => select(e.currentTarget.value)}
      >
        <optgroup label={t("bots.presets")}>
          {#each presets as p (p.key)}
            <option value="preset:{p.key}">{p.name}</option>
          {/each}
        </optgroup>
        {#if saved.length}
          <optgroup label={t("bots.saved")}>
            {#each saved as b (b.id)}
              <option value="saved:{b.id}">{b.name}</option>
            {/each}
          </optgroup>
        {/if}
      </select>
      {#if description}<span class="mt-1 block text-slate-600">{description}</span>{/if}
    </label>
  {/if}

  <div>
    <p class="mb-1 text-sm font-medium">{t("profile.character")}</p>
    <CharacterPicker value={character} allowAny onChange={(c) => (character = c)} />
  </div>

  <details class="rounded-md border border-slate-200 p-3" open={modified || !!editing}>
    <summary class="cursor-pointer text-sm font-semibold">{t("bots.advanced")}</summary>
    <div class="mt-3 grid gap-6 md:grid-cols-3">
      <fieldset class="space-y-3">
        <legend class="mb-2 font-semibold">{t("bots.cards")}</legend>
        <label class="block text-sm">
          <span class="font-medium">{t("bots.cardOrder")}</span>
          <select class="input mt-1" name="card_order" bind:value={settings.card_order}>
            {#each CARD_ORDERS as o (o)}
              <option value={o}>{t(`bots.cardOrder.${o}`)}</option>
            {/each}
          </select>
        </label>
        <label class="block text-sm">
          <span class="font-medium">{t("bots.bluff")}: {Math.round(settings.bluff * 100)}%</span>
          <input
            class="mt-1 w-full"
            type="range"
            min="0"
            max="1"
            step="0.05"
            name="bluff"
            bind:value={settings.bluff}
          />
        </label>
      </fieldset>

      <fieldset class="space-y-3">
        <legend class="mb-2 font-semibold">Envido</legend>
        {@render policy("envido_sing", t("bots.sing"))}
        {#if settings.envido_sing === "threshold"}{@render tanto("envido_sing_threshold")}{/if}
        <label class="block text-sm">
          <span class="font-medium">{t("bots.envidoCall")}</span>
          <select class="input mt-1" name="envido_call" bind:value={settings.envido_call}>
            {#each ENVIDO_CALLS as c (c)}
              <option value={c}>{ENVIDO_CALL_LABELS[c]}</option>
            {/each}
          </select>
        </label>
        {@render policy("envido_accept", t("bots.accept"))}
        {#if settings.envido_accept === "threshold"}{@render tanto("envido_accept_threshold")}{/if}
        <label class="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="envido_raise"
            checked={settings.envido_raise_threshold !== null}
            onchange={(e) => toggleRaise("envido_raise_threshold", e.currentTarget.checked)}
          />
          <span class="font-medium">{t("bots.raise")}</span>
        </label>
        {#if settings.envido_raise_threshold !== null}
          <label class="block text-sm">
            <span class="font-medium">{t("bots.raiseWhen")}</span>
            <input
              class="input mt-1"
              type="number"
              min="0"
              max="33"
              name="envido_raise_threshold"
              bind:value={settings.envido_raise_threshold}
            />
          </label>
        {/if}
      </fieldset>

      <fieldset class="space-y-3">
        <legend class="mb-2 font-semibold">Truco</legend>
        {@render policy("truco_sing", t("bots.sing"))}
        {#if settings.truco_sing === "threshold"}
          {@render rank("truco_sing_threshold", t("bots.threshold"))}
        {/if}
        {@render policy("truco_accept", t("bots.accept"))}
        {#if settings.truco_accept === "threshold"}
          {@render rank("truco_accept_threshold", t("bots.threshold"))}
        {/if}
        <label class="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="truco_raise"
            checked={settings.truco_raise_threshold !== null}
            onchange={(e) => toggleRaise("truco_raise_threshold", e.currentTarget.checked)}
          />
          <span class="font-medium">{t("bots.raise")} (retruco / vale cuatro)</span>
        </label>
        {#if settings.truco_raise_threshold !== null}
          {@render rank("truco_raise_threshold", t("bots.raiseWhen"))}
        {/if}
      </fieldset>
    </div>
    {#if modified}<p class="mt-3 text-sm text-amber-700">{t("bots.modified")}</p>{/if}
  </details>

  <form class="flex max-w-lg items-end gap-2" onsubmit={save}>
    <label class="block flex-1 text-sm">
      <span class="font-medium">{t("bots.name")}</span>
      <input class="input mt-1" name="name" maxlength="40" bind:value={name} />
    </label>
    <button class="btn btn-primary" type="submit" disabled={!name.trim() || saving}>
      {t("bots.save")}
    </button>
    {#if onCancel}
      <button class="btn" type="button" onclick={onCancel}>{t("bots.cancel")}</button>
    {/if}
  </form>
  {#if message}
    <p role="status" class="text-sm {message.ok ? 'text-green-700' : 'text-red-600'}">
      {message.text}
    </p>
  {/if}
</div>
