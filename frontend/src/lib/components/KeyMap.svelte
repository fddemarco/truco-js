<script lang="ts">
  import { t } from "$lib/i18n.svelte";
  import { commandLabel, KEY_GROUPS, keyLabel } from "$lib/keys";
  import { bindings } from "$lib/profile.svelte";

  /** Señas only matter at an interactive table. */
  let { senas = true }: { senas?: boolean } = $props();

  const keys = $derived(bindings());
  const groups = $derived(
    KEY_GROUPS.filter((g) => senas || g.title !== "keys.group.senas").map((g) => ({
      ...g,
      commands: g.commands.filter((c) => keys[c]),
    })),
  );
</script>

<!-- The keys in use, floating over the table while Tab is held. Read-only: they are changed
     in the settings. -->
<div
  class="theme-table table-glass pointer-events-none fixed top-1/2 left-1/2 z-[70] w-[min(56rem,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-2xl p-5"
  role="dialog"
  aria-label={t("keymap.title")}
  data-testid="keymap"
>
  <div class="mb-3 flex items-baseline justify-between gap-4">
    <h2 class="text-lg font-black tracking-wide text-amber-200">{t("keymap.title")}</h2>
    <span class="text-xs text-amber-100/60">{t("keymap.hint")}</span>
  </div>
  <div class="columns-1 gap-6 sm:columns-2 lg:columns-3">
    {#each groups as group (group.title)}
      {#if group.commands.length}
        <section class="mb-4 break-inside-avoid">
          <h3 class="mb-1 text-[0.65rem] font-bold tracking-widest text-amber-300/80 uppercase">
            {t(group.title)}
          </h3>
          <ul class="space-y-0.5">
            {#each group.commands as c (c)}
              <li class="flex items-center justify-between gap-3 text-sm">
                <span class="truncate text-amber-50/90">{commandLabel(c)}</span>
                <kbd
                  class="min-w-7 rounded-md border border-amber-200/30 bg-black/30 px-1.5 text-center font-mono text-xs font-bold text-amber-100 shadow-[inset_0_-2px_0_rgb(0_0_0/0.4)]"
                  >{keyLabel(keys[c])}</kbd
                >
              </li>
            {/each}
          </ul>
        </section>
      {/if}
    {/each}
  </div>
</div>
