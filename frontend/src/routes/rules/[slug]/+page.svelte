<script lang="ts">
  import { page } from "$app/state";
  import { i18n, t } from "$lib/i18n.svelte";
  import { ruleHtml, SECTIONS } from "$lib/rules";

  const index = $derived(SECTIONS.findIndex((s) => s.slug === page.params.slug));
  const section = $derived(SECTIONS[index]);
  const prev = $derived(SECTIONS[index - 1]);
  const next = $derived(SECTIONS[index + 1]);
  // Our own markdown, bundled at build time: safe to render as HTML.
  const html = $derived(section ? ruleHtml(section.slug, i18n.locale) : undefined);
</script>

<article class="card">
  {#if section && html}
    <h1 class="text-xl font-semibold">{section.title[i18n.locale]}</h1>
    <div class="prose prose-slate mt-4 max-w-none prose-table:text-sm">
      {@html html}
    </div>
    <nav class="mt-6 flex justify-between border-t border-slate-200 pt-4 text-sm">
      {#if prev}
        <a class="text-indigo-600 hover:underline" href="/rules/{prev.slug}">
          ← {t("rules.prev")}: {prev.title[i18n.locale]}
        </a>
      {:else}<span></span>{/if}
      {#if next}
        <a class="text-indigo-600 hover:underline" href="/rules/{next.slug}">
          {t("rules.next")}: {next.title[i18n.locale]} →
        </a>
      {/if}
    </nav>
  {:else}
    <p class="text-sm text-slate-600">{t("rules.notFound")}</p>
  {/if}
</article>
