<script lang="ts">
  import { i18n, LOCALES, setLocale, t } from "$lib/i18n.svelte";

  const LANGUAGE_NAMES = { es: "Español", en: "English" };
</script>

<div class="flex gap-2" role="group" aria-label={t("lang.label")}>
  {#each LOCALES as locale (locale)}
    <button
      class="btn {i18n.locale === locale ? 'btn-primary' : ''}"
      aria-pressed={i18n.locale === locale}
      onclick={() => setLocale(locale)}
    >
      {LANGUAGE_NAMES[locale]}
    </button>
  {/each}
</div>
