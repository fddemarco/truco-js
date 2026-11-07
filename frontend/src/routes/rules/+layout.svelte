<script lang="ts">
  import { page } from "$app/state";
  import { i18n, t } from "$lib/i18n.svelte";
  import { SECTIONS } from "$lib/rules";

  let { children } = $props();
</script>

<div class="flex flex-col gap-6 md:flex-row">
  <aside class="md:w-60 md:shrink-0">
    <h2 class="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
      {t("rules.contents")}
    </h2>
    <ol class="space-y-1 text-sm">
      {#each SECTIONS as section (section.slug)}
        <li>
          <a
            href="/rules/{section.slug}"
            class="block rounded px-2 py-1 {page.params.slug === section.slug
              ? 'bg-indigo-50 font-semibold text-indigo-700'
              : 'text-slate-700 hover:bg-slate-100'}"
          >
            {section.title[i18n.locale]}
          </a>
        </li>
      {/each}
    </ol>
  </aside>
  <div class="min-w-0 flex-1">
    {@render children()}
  </div>
</div>
