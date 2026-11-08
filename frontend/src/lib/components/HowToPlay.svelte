<script lang="ts">
  import { SENA_NAMES, SENAS, SPOTS } from "$lib/avatar/avatar";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import { keyLabel, PLAY_COMMANDS, type PlayCommand } from "$lib/keys";
  import { bindings } from "$lib/profile.svelte";

  const keys = $derived(bindings());
  const SECTIONS: MessageKey[] = [
    "howto.goal",
    "howto.mano",
    "howto.ranks",
    "howto.envido",
    "howto.truco",
    "howto.picaPica",
  ];
  // The keys a player needs most, in the order of play.
  const MAIN: PlayCommand[] = [
    "card1",
    "card2",
    "card3",
    "quiero",
    "no_quiero",
    "envido",
    "real_envido",
    "falta_envido",
    "truco",
    "son_buenas",
    "me_voy_al_mazo",
    "cut",
    "look_left",
    "look_right",
  ];
  const rest = PLAY_COMMANDS.filter((c) => !MAIN.includes(c));
</script>

<div class="space-y-5 text-sm">
  <div class="grid gap-3 md:grid-cols-2">
    {#each SECTIONS as key (key)}
      <section class="rounded-xl bg-slate-50 p-3">
        <h3 class="font-semibold">{t(`${key}.title` as MessageKey)}</h3>
        <p class="mt-1 text-slate-700">{t(key)}</p>
      </section>
    {/each}
  </div>

  <section>
    <h3 class="mb-2 font-semibold">{t("howto.keys")}</h3>
    <div class="grid gap-x-6 gap-y-1 sm:grid-cols-2" data-testid="howto-keys">
      {#each [...MAIN, ...rest] as c (c)}
        <div class="flex items-center justify-between border-b border-slate-100 py-1">
          <span>{t(`keys.cmd.${c}` as MessageKey)}</span>
          <kbd
            class="min-w-8 rounded-md border border-slate-300 bg-white px-2 text-center font-mono font-bold"
            >{keyLabel(keys[c]) || "—"}</kbd
          >
        </div>
      {/each}
    </div>
  </section>

  <section>
    <h3 class="font-semibold">{t("howto.senas.title")}</h3>
    <p class="mb-2 text-slate-600">{t("howto.senas")}</p>
    <table class="table" data-testid="howto-senas">
      <thead>
        <tr>
          <th>{t("howto.senas.meaning")}</th>
          <th>{t("howto.senas.gesture")}</th>
          <th>{t("howto.senas.key")}</th>
        </tr>
      </thead>
      <tbody>
        {#each SENAS as s (s)}
          <tr>
            <td class="font-semibold">{SENA_NAMES[s]}</td>
            <td>{t(`sena.gesture.${SPOTS[s][0]}` as MessageKey)}</td>
            <td><kbd class="font-mono font-bold">{keyLabel(keys[s]) || "—"}</kbd></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <p class="text-slate-600">
    {t("howto.more")}
    <a class="font-semibold text-indigo-700 underline" href="/rules">{t("nav.rules")}</a>
  </p>
</div>
