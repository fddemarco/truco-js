<script lang="ts">
  import { t } from "$lib/i18n.svelte";
  import { profile, updateProfile } from "$lib/profile.svelte";

  const VOLUMES = [
    ["musicVolume", "settings.music"],
    ["sfxVolume", "settings.sfx"],
  ] as const;
</script>

<div class="max-w-sm space-y-4">
  {#each VOLUMES as [key, label] (key)}
    <label class="block text-sm">
      <span class="font-semibold">{t(label)}: {Math.round(profile[key] * 100)}%</span>
      <input
        class="mt-1 w-full"
        type="range"
        min="0"
        max="1"
        step="0.05"
        value={profile[key]}
        oninput={(e) => updateProfile({ [key]: Number(e.currentTarget.value) })}
      />
    </label>
  {/each}
  <label class="flex items-center gap-2 text-sm font-semibold">
    <input
      type="checkbox"
      checked={profile.muted}
      onchange={(e) => updateProfile({ muted: e.currentTarget.checked })}
    />
    {t("settings.mute")}
  </label>
</div>
