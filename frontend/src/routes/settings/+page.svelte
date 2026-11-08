<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import CharacterPicker from "$lib/components/CharacterPicker.svelte";
  import HowToPlay from "$lib/components/HowToPlay.svelte";
  import KeyBindings from "$lib/components/KeyBindings.svelte";
  import LanguageSettings from "$lib/components/LanguageSettings.svelte";
  import SoundSettings from "$lib/components/SoundSettings.svelte";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import { profile, updateProfile } from "$lib/profile.svelte";

  // Bots are set up with a new game (play/, its Bots tab), never during one.
  const TABS = ["profile", "howto", "keys", "sound", "language"] as const;
  type Tab = (typeof TABS)[number];
  const tab = $derived.by((): Tab => {
    const wanted = page.url.searchParams.get("tab");
    return TABS.find((id) => id === wanted) ?? "profile";
  });
</script>

<section class="card space-y-5">
  <h1 class="text-xl font-semibold">{t("settings.title")}</h1>
  <div class="flex gap-1 border-b border-slate-200" role="tablist">
    {#each TABS as id (id)}
      <button
        role="tab"
        aria-selected={tab === id}
        class="-mb-px border-b-2 px-3 py-2 text-sm font-semibold {tab === id
          ? 'border-indigo-600 text-indigo-700'
          : 'border-transparent text-slate-500 hover:text-slate-800'}"
        onclick={() => goto(`?tab=${id}`, { replaceState: true, noScroll: true })}
      >
        {t(`settings.${id}` as MessageKey)}
      </button>
    {/each}
  </div>

  {#if tab === "profile"}
    <div class="max-w-2xl space-y-4">
      <label class="block max-w-sm">
        <span class="text-sm font-semibold">{t("profile.name")}</span>
        <input
          class="input mt-1"
          maxlength="40"
          value={profile.name}
          onchange={(e) => {
            if (e.currentTarget.value.trim()) updateProfile({ name: e.currentTarget.value });
          }}
        />
      </label>
      <div>
        <p class="mb-1 text-sm font-semibold">{t("profile.character")}</p>
        <CharacterPicker
          value={profile.character}
          onChange={(c) => c && updateProfile({ character: c })}
        />
      </div>
    </div>
  {:else if tab === "howto"}
    <HowToPlay />
  {:else if tab === "keys"}
    <KeyBindings />
  {:else if tab === "sound"}
    <SoundSettings />
  {:else}
    <LanguageSettings />
  {/if}
</section>
