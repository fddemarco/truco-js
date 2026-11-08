<script lang="ts">
  import { SENA_NAMES, SENAS } from "$lib/avatar/avatar";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import {
    bindable,
    KEY_PRESETS,
    keyLabel,
    PRESET_BINDINGS,
    rebind,
    type Command,
    type KeyChoice,
    type PlayCommand,
  } from "$lib/keys";
  import { bindings, profile, updateProfile } from "$lib/profile.svelte";

  const GROUPS: { title: MessageKey; commands: Command[] }[] = [
    { title: "keys.group.cards", commands: ["card1", "card2", "card3"] },
    {
      title: "keys.group.cantos",
      commands: [
        "quiero",
        "no_quiero",
        "envido",
        "real_envido",
        "falta_envido",
        "truco",
        "son_buenas",
      ],
    },
    {
      title: "keys.group.other",
      commands: [
        "me_voy_al_mazo",
        "nos_vamos_al_mazo",
        "objetar",
        "perdon",
        "mostrar",
        "tapar",
        "reclamar",
      ],
    },
    { title: "keys.group.table", commands: ["cut", "look_left", "look_right"] },
    { title: "keys.group.senas", commands: SENAS },
  ];
  const CHOICES: KeyChoice[] = [...KEY_PRESETS, "custom"];

  const current = $derived(bindings());
  const custom = $derived(profile.keys === "custom");
  let capturing = $state<Command | null>(null);

  function labelOf(c: Command): string {
    return c.startsWith("sena_")
      ? SENA_NAMES[c as keyof typeof SENA_NAMES]
      : t(`keys.cmd.${c as PlayCommand}` as MessageKey);
  }

  function choose(choice: KeyChoice) {
    capturing = null;
    if (choice === "custom" && profile.keys !== "custom") {
      // Custom starts from the keys in use, so nothing changes until the player edits it.
      updateProfile({ keys: "custom", customKeys: { ...current } });
    } else {
      updateProfile({ keys: choice });
    }
  }

  function resetTo(preset: (typeof KEY_PRESETS)[number]) {
    updateProfile({ customKeys: { ...PRESET_BINDINGS[preset] } });
  }

  // Capture the next key press for the command being edited.
  function capture(e: KeyboardEvent) {
    if (!capturing) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (e.code === "Escape") {
      capturing = null;
      return;
    }
    if (e.code === "Backspace" || e.code === "Delete") {
      updateProfile({ customKeys: { ...current, [capturing]: "" } });
      capturing = null;
      return;
    }
    if (!bindable(e.code)) return;
    updateProfile({ customKeys: rebind(current, capturing, e.code) });
    capturing = null;
  }
</script>

<svelte:window onkeydowncapture={capture} />

<div class="space-y-4">
  <div class="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label={t("keys.layout")}>
    {#each CHOICES as choice (choice)}
      <button
        type="button"
        role="radio"
        aria-checked={profile.keys === choice}
        class="rounded-xl border-2 p-3 text-left transition {profile.keys === choice
          ? 'border-indigo-500 bg-indigo-50'
          : 'border-slate-200 hover:border-slate-300'}"
        onclick={() => choose(choice)}
      >
        <span class="block font-semibold">{t(`keys.preset.${choice}` as MessageKey)}</span>
        <span class="block text-xs text-slate-600"
          >{t(`keys.preset.${choice}.hint` as MessageKey)}</span
        >
      </button>
    {/each}
  </div>

  {#if custom}
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <span class="text-slate-600">{t("keys.customHelp")}</span>
      {#each KEY_PRESETS as preset (preset)}
        <button type="button" class="btn" onclick={() => resetTo(preset)}>
          {t("keys.resetTo", { name: t(`keys.preset.${preset}` as MessageKey) })}
        </button>
      {/each}
    </div>
  {/if}

  <div class="grid gap-4 md:grid-cols-2" data-testid="bindings">
    {#each GROUPS as group (group.title)}
      <section>
        <h3 class="mb-1 text-xs font-semibold tracking-wide text-slate-500 uppercase">
          {t(group.title)}
        </h3>
        <ul class="divide-y divide-slate-100 rounded-lg border border-slate-200">
          {#each group.commands as c (c)}
            <li class="flex items-center justify-between gap-2 px-3 py-1.5 text-sm">
              <span>{labelOf(c)}</span>
              {#if custom}
                <button
                  type="button"
                  class="min-w-16 rounded-md border px-2 py-0.5 font-mono text-sm font-bold {capturing ===
                  c
                    ? 'animate-pulse border-amber-500 bg-amber-50'
                    : current[c]
                      ? 'border-slate-300 bg-slate-50'
                      : 'border-dashed border-red-300 text-red-600'}"
                  aria-label="{labelOf(c)}: {current[c] ? keyLabel(current[c]) : t('keys.unbound')}"
                  onclick={() => (capturing = capturing === c ? null : c)}
                >
                  {capturing === c ? t("keys.press") : current[c] ? keyLabel(current[c]) : "—"}
                </button>
              {:else}
                <kbd
                  class="min-w-8 rounded-md border border-slate-300 bg-slate-50 px-2 py-0.5 text-center font-mono font-bold"
                >
                  {keyLabel(current[c]) || "—"}
                </kbd>
              {/if}
            </li>
          {/each}
        </ul>
      </section>
    {/each}
  </div>
</div>
