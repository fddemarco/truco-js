<script lang="ts">
  import { t } from "$lib/i18n.svelte";
  import HowToPlay from "./HowToPlay.svelte";
  import KeyBindings from "./KeyBindings.svelte";

  let { onClose }: { onClose: () => void } = $props();
  let tab = $state<"howto" | "keys">("howto");
</script>

<svelte:window onkeydown={(e) => e.code === "Escape" && onClose()} />

<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm"
  role="dialog"
  aria-modal="true"
  aria-label={t("help.title")}
>
  <div class="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl bg-white shadow-2xl">
    <div class="flex items-center gap-2 border-b border-slate-200 px-4 pt-3">
      <div class="flex gap-1" role="tablist">
        {#each [["howto", "help.howto"], ["keys", "help.keys"]] as const as [id, label] (id)}
          <button
            role="tab"
            aria-selected={tab === id}
            class="-mb-px border-b-2 px-3 py-2 text-sm font-semibold {tab === id
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'}"
            onclick={() => (tab = id)}>{t(label)}</button
          >
        {/each}
      </div>
      <button
        class="ml-auto rounded-full px-2 text-2xl leading-none text-slate-500 hover:text-slate-900"
        aria-label={t("help.close")}
        onclick={onClose}>×</button
      >
    </div>
    <div class="overflow-y-auto p-4">
      {#if tab === "howto"}<HowToPlay />{:else}<KeyBindings />{/if}
    </div>
  </div>
</div>
