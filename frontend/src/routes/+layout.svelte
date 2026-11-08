<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { playlistFor, setPlaylist, startMusic, syncMusicVolume } from "$lib/audio.svelte";
  import WelcomeDialog from "$lib/components/WelcomeDialog.svelte";
  import { installGlobalHandlers, log } from "$lib/log";
  import { LOGO } from "$lib/cards";
  import { i18n, t } from "$lib/i18n.svelte";
  import { profile } from "$lib/profile.svelte";
  import "../app.css";

  let { children } = $props();

  const home = $derived(page.url.pathname === "/");
  // At the table its own menu has settings and leaving: no corner links that drop the game.
  const atTable = $derived(page.url.pathname.startsWith("/play/"));

  $effect(() => {
    document.documentElement.lang = i18n.locale;
  });

  onMount(() => {
    installGlobalHandlers();
    log.info("ui.started", { path: page.url.pathname, locale: i18n.locale });
    // Try the music right away; browsers that block sound before a gesture get another try on
    // each one until it plays (pointerdown alone doesn't count everywhere, e.g. on touch).
    const gestures = ["pointerdown", "pointerup", "click", "touchend", "keydown"] as const;
    const stop = () => gestures.forEach((g) => window.removeEventListener(g, start));
    const start = () => startMusic().then((playing) => playing && stop());
    gestures.forEach((g) => window.addEventListener(g, start));
    start();
    return stop;
  });

  // Each part of the app has its own music; the volume follows the settings.
  $effect(() => setPlaylist(playlistFor(page.url.pathname)));
  $effect(syncMusicVolume);

  $effect(() => {
    log.info("ui.navigated", { path: page.url.pathname });
  });
</script>

<svelte:head><title>Truco</title></svelte:head>

{#snippet icon(href: string, label: string, path: string)}
  <a
    {href}
    class="rounded-full bg-white/90 p-2 text-slate-700 shadow ring-1 ring-slate-200 backdrop-blur hover:bg-white hover:text-slate-950"
    aria-label={label}
    title={label}
  >
    <svg
      viewBox="0 0 24 24"
      class="h-5 w-5"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      {@html path}
    </svg>
  </a>
{/snippet}

<div class="min-h-screen">
  <!-- No top bar: a corner with home, rules and settings. -->
  {#if !home && !atTable}
    <a href="/" class="fixed top-3 left-3 z-40" aria-label={t("nav.home")}>
      <img
        src={LOGO}
        alt="Truco"
        width="200"
        height="72"
        class="h-9 w-auto rounded-lg bg-white/90 px-2 py-0.5 shadow"
      />
    </a>
  {/if}
  {#if !atTable}<nav class="fixed top-3 right-3 z-40 flex gap-2" aria-label={t("nav.menu")}>
      {@render icon(
        "/rules",
        t("nav.rules"),
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
      )}
      {@render icon(
        "/settings",
        t("nav.settings"),
        '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
      )}
    </nav>{/if}
  <main class="mx-auto max-w-6xl px-4 pt-16 pb-6">
    {@render children()}
  </main>
  {#if !profile.name}<WelcomeDialog />{/if}
</div>
