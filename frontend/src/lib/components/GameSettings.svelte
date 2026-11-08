<script lang="ts" module>
  export type GameSettingsTab = "howto" | "keys" | "sound" | "language";
</script>

<script lang="ts">
  import { untrack } from "svelte";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import HowToPlay from "./HowToPlay.svelte";
  import KeyBindings from "./KeyBindings.svelte";
  import LanguageSettings from "./LanguageSettings.svelte";
  import SoundSettings from "./SoundSettings.svelte";

  const TABS: GameSettingsTab[] = ["howto", "keys", "sound", "language"];

  /**
   * Settings over the table: nothing here leaves the game. Bots, the profile and the scoring
   * are set before a game starts, so they are not here.
   */
  let { onClose, tab: first = "howto" }: { onClose: () => void; tab?: GameSettingsTab } = $props();
  let tab = $state(untrack(() => first));
</script>

<svelte:window onkeydown={(e) => e.code === "Escape" && onClose()} />

<div
  class="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm"
  role="dialog"
  aria-modal="true"
  aria-label={t("nav.settings")}
>
  <div class="theme-table table-panel flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl">
    <div class="flex items-center gap-2 border-b border-amber-100/15 px-4 pt-3">
      <div class="flex gap-1" role="tablist">
        {#each TABS as id (id)}
          <button
            role="tab"
            aria-selected={tab === id}
            class="-mb-px border-b-2 px-3 py-2 text-sm font-semibold {tab === id
              ? 'border-amber-400 text-amber-200'
              : 'border-transparent text-amber-100/60 hover:text-amber-50'}"
            onclick={() => (tab = id)}>{t(`settings.${id}` as MessageKey)}</button
          >
        {/each}
      </div>
      <button
        class="ml-auto rounded-full px-2 text-2xl leading-none text-amber-100/60 hover:text-amber-50"
        aria-label={t("help.close")}
        onclick={onClose}>×</button
      >
    </div>
    <div class="overflow-y-auto p-4">
      {#if tab === "howto"}<HowToPlay />
      {:else if tab === "keys"}<KeyBindings />
      {:else if tab === "sound"}<SoundSettings />
      {:else}<LanguageSettings />{/if}
    </div>
  </div>
</div>
