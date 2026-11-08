<script lang="ts">
  import { untrack } from "svelte";
  import { LOGO } from "$lib/cards";
  import { t } from "$lib/i18n.svelte";
  import { profile, updateProfile } from "$lib/profile.svelte";
  import CharacterPicker from "./CharacterPicker.svelte";

  // First visit: the player picks a name and a character before anything else.
  let name = $state(untrack(() => profile.name));
  let character = $state(untrack(() => profile.character));

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (name.trim()) updateProfile({ name, character });
  }
</script>

<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
  role="dialog"
  aria-modal="true"
  aria-labelledby="welcome-title"
>
  <form class="w-full max-w-2xl space-y-5 rounded-2xl bg-white p-6 shadow-2xl" onsubmit={submit}>
    <div class="flex flex-col items-center text-center">
      <img src={LOGO} alt="Truco" width="200" height="72" class="h-14 w-auto" />
      <h1 id="welcome-title" class="mt-3 text-2xl font-black">{t("welcome.title")}</h1>
      <p class="text-sm text-slate-600">{t("welcome.intro")}</p>
    </div>
    <label class="block">
      <span class="text-sm font-semibold">{t("profile.name")}</span>
      <!-- svelte-ignore a11y_autofocus -->
      <input
        class="input mt-1 text-lg"
        name="name"
        maxlength="40"
        autocomplete="nickname"
        autofocus
        bind:value={name}
      />
    </label>
    <div>
      <p class="mb-1 text-sm font-semibold">{t("profile.character")}</p>
      <CharacterPicker value={character} onChange={(c) => c && (character = c)} />
    </div>
    <button class="btn btn-primary w-full justify-center py-2 text-base" disabled={!name.trim()}>
      {t("welcome.start")}
    </button>
  </form>
</div>
