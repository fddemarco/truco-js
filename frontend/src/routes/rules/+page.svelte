<script lang="ts">
  import { i18n, t } from "$lib/i18n.svelte";
  import { SECTIONS } from "$lib/rules";
</script>

<section class="card">
  <h1 class="text-xl font-semibold">{t("rules.title")}</h1>
  <p class="mt-1 text-sm text-slate-600">{t("rules.intro")}</p>
  <ol class="mt-4 grid gap-3 sm:grid-cols-2">
    {#each SECTIONS as section (section.slug)}
      <li>
        <a
          href="/rules/{section.slug}"
          class="block rounded-md border border-slate-200 p-3 hover:border-indigo-300 hover:bg-indigo-50"
        >
          <span class="font-medium">{section.title[i18n.locale]}</span>
          <span class="block text-xs text-slate-500">
            {t("rules.chapters")}
            {section.chapters}
          </span>
        </a>
      </li>
    {/each}
  </ol>
  <p class="mt-4 text-xs text-slate-500">{t("rules.source")}</p>
</section>
