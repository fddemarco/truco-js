<script lang="ts">
  import { avatarPortrait, CHARACTER_NAMES, CHARACTERS, type Character } from "$lib/avatar/avatar";
  import { t } from "$lib/i18n.svelte";

  interface Props {
    value: Character | null;
    onChange: (character: Character | null) => void;
    /** Offer "any": the table gives the bot whichever character is free. */
    allowAny?: boolean;
    /** Characters already taken by other seats: shown, but not selectable. */
    taken?: Character[];
  }

  let { value, onChange, allowAny = false, taken = [] }: Props = $props();
</script>

<div class="grid grid-cols-3 gap-2 sm:grid-cols-6" role="group" aria-label={t("profile.character")}>
  {#each CHARACTERS as c (c)}
    {@const selected = value === c}
    <button
      type="button"
      class="flex flex-col items-center gap-1 rounded-xl border-2 p-1.5 text-xs font-semibold transition {selected
        ? 'border-amber-400 bg-amber-50 shadow-md'
        : 'border-transparent hover:border-slate-300'} disabled:opacity-30"
      aria-pressed={selected}
      disabled={taken.includes(c) && !selected}
      onclick={() => onChange(c)}
    >
      <img
        src={avatarPortrait(c)}
        alt=""
        width="96"
        height="96"
        class="h-20 w-full rounded-lg bg-slate-100 object-contain"
      />
      {CHARACTER_NAMES[c]}
    </button>
  {/each}
  {#if allowAny}
    <button
      type="button"
      class="col-span-3 rounded-xl border-2 p-2 text-xs font-semibold sm:col-span-6 {value === null
        ? 'border-amber-400 bg-amber-50'
        : 'border-transparent hover:border-slate-300'}"
      aria-pressed={value === null}
      onclick={() => onChange(null)}
    >
      {t("profile.anyCharacter")}
    </button>
  {/if}
</div>
