<script lang="ts">
  import { LOGO } from "$lib/cards";
  import { t } from "$lib/i18n.svelte";
</script>

<!-- The start screen: two ways to play up front, rules and bots as small corner icons. The
     banner (static/ui/banner.webp) has fileteado corners and an open paper area on the left,
     where the menu sits; under it, the felt green. -->
<section
  class="hero relative mx-auto mt-6 max-w-5xl overflow-hidden rounded-2xl px-6 py-12 shadow-xl sm:aspect-[16/9] sm:px-0 sm:py-0"
>
  <a
    href="/rules"
    class="absolute top-4 left-4 z-10 rounded-full bg-slate-950/40 p-2.5 text-white backdrop-blur hover:bg-slate-950/60"
    aria-label={t("home.rules")}
    title={t("home.rules")}
  >
    <!-- book -->
    <svg
      viewBox="0 0 24 24"
      class="h-6 w-6"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  </a>
  <a
    href="/settings"
    class="absolute top-4 right-4 z-10 rounded-full bg-slate-950/40 p-2.5 text-white backdrop-blur hover:bg-slate-950/60"
    aria-label={t("home.settings")}
    title={t("home.settings")}
  >
    <!-- gear -->
    <svg
      viewBox="0 0 24 24"
      class="h-6 w-6"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="3" />
      <path
        d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
      />
    </svg>
  </a>

  <div
    class="flex h-full flex-col justify-center sm:absolute sm:inset-y-0 sm:left-[15%] sm:w-[42%]"
  >
    <div class="flex flex-col items-center text-center">
      <img
        src={LOGO}
        alt="Truco"
        width="200"
        height="72"
        class="h-20 w-auto rounded-lg bg-white/90 px-3 py-1 shadow"
      />
      <p class="mt-3 font-medium text-amber-950/80">{t("home.tagline")}</p>
    </div>

    <div class="mt-8 grid gap-4 sm:grid-cols-2">
      <a
        href="/play?where=online"
        class="group rounded-xl bg-amber-400 px-6 py-6 text-center text-amber-950 shadow-lg transition hover:-translate-y-1 hover:bg-amber-300"
      >
        <span class="block text-2xl font-black">{t("home.online")}</span>
        <span class="mt-1 block text-sm text-amber-900">{t("home.onlineHint")}</span>
      </a>
      <a
        href="/play?where=local"
        class="group rounded-xl bg-white px-6 py-6 text-center text-slate-900 shadow-lg transition hover:-translate-y-1 hover:bg-slate-50"
      >
        <span class="block text-2xl font-black">{t("home.local")}</span>
        <span class="mt-1 block text-sm text-slate-600">{t("home.localHint")}</span>
      </a>
    </div>
  </div>
</section>

<style>
  /* Paper colour under the banner, for when the image is missing or still loading. */
  .hero {
    background:
      url("/ui/banner.webp") center / cover,
      #efe4cc;
  }
</style>
