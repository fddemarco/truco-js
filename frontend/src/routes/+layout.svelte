<script lang="ts">
  import { page } from "$app/state";
  import { LOGO } from "$lib/cards";
  import { i18n, LOCALES, setLocale, t, type MessageKey } from "$lib/i18n.svelte";
  import "../app.css";

  let { children } = $props();

  const nav: { href: string; label: MessageKey }[] = [{ href: "/rules", label: "nav.rules" }];

  $effect(() => {
    document.documentElement.lang = i18n.locale;
  });
</script>

<svelte:head><title>Truco</title></svelte:head>

<div class="min-h-screen">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
      <a href="/"><img src={LOGO} alt="Truco" width="200" height="72" class="h-9 w-auto" /></a>
      <nav class="flex gap-4 text-sm">
        {#each nav as item (item.href)}
          <a
            href={item.href}
            class={page.url.pathname.startsWith(item.href)
              ? "font-semibold text-indigo-600"
              : "text-slate-600 hover:text-slate-900"}
          >
            {t(item.label)}
          </a>
        {/each}
      </nav>
      <div class="ml-auto flex gap-1 text-xs" role="group" aria-label={t("lang.label")}>
        {#each LOCALES as locale (locale)}
          <button
            class="rounded px-2 py-1 font-medium uppercase {i18n.locale === locale
              ? 'bg-indigo-600 text-white'
              : 'text-slate-600 hover:bg-slate-100'}"
            aria-pressed={i18n.locale === locale}
            onclick={() => setLocale(locale)}
          >
            {locale}
          </button>
        {/each}
      </div>
    </div>
  </header>
  <main class="mx-auto max-w-6xl px-4 py-6">
    {@render children()}
  </main>
</div>
