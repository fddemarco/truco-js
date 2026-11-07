<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import {
    api,
    errorMessage,
    type BotConfig,
    type BotPreset,
    type RuleMode,
    type SeatSetup,
  } from "$lib/api/client";
  import { saveToken } from "$lib/game";
  import { t } from "$lib/i18n.svelte";

  let presets = $state<BotPreset[]>([]);
  let saved = $state<BotConfig[]>([]);
  let mode = $state<RuleMode>("strict");
  let where = $state<"local" | "online">("local");
  let error = $state<string | null>(null);
  let busy = $state(false);

  interface Row {
    kind: "human" | "bot";
    name: string;
    bot: string; // "preset:<key>" or "saved:<id>"
  }
  let rows = $state<Row[]>(
    Array.from({ length: 6 }, (_, i) => ({
      kind: i === 0 ? "human" : "bot",
      name: "",
      bot: "preset:prolijo",
    })),
  );

  onMount(async () => {
    const [p, b] = await Promise.all([api.GET("/api/bots/presets"), api.GET("/api/bots")]);
    presets = p.data ?? [];
    saved = b.data ?? [];
  });

  const humans = $derived(rows.flatMap((r, i) => (r.kind === "human" ? [i] : [])));

  function setup(row: Row): SeatSetup {
    if (row.kind === "human") return { kind: "human", name: row.name };
    const [kind, id] = row.bot.split(":");
    return kind === "saved"
      ? { kind: "bot", name: row.name, bot_id: Number(id), bot_preset: null }
      : { kind: "bot", name: row.name, bot_preset: id, bot_id: null };
  }

  async function start(event: SubmitEvent) {
    event.preventDefault();
    if (!humans.length) {
      error = t("play.needHuman");
      return;
    }
    busy = true;
    error = null;
    const created = await api.POST("/api/games", { body: { mode, seats: rows.map(setup) } });
    if (created.error || !created.data) {
      error = errorMessage(created.error);
      busy = false;
      return;
    }
    const id = created.data.id;
    // Local: this device takes every human seat. Online: only the first one.
    for (const seat of where === "local" ? humans : humans.slice(0, 1)) {
      const joined = await api.POST("/api/games/{game_id}/join", {
        params: { path: { game_id: id } },
        body: { seat, name: rows[seat].name },
      });
      if (joined.error || !joined.data) {
        error = errorMessage(joined.error);
        busy = false;
        return;
      }
      saveToken(id, seat, joined.data.token);
    }
    await goto(`/play/${id}`);
  }
</script>

<form class="card space-y-5" onsubmit={start}>
  <div>
    <h1 class="text-xl font-semibold">{t("play.title")}</h1>
    <p class="mt-1 text-sm text-slate-600">{t("play.intro")}</p>
  </div>

  <fieldset class="space-y-1 text-sm">
    <legend class="mb-1 font-semibold">{t("play.mode")}</legend>
    {#each ["strict", "interactive"] as const as m (m)}
      <label class="flex items-center gap-2">
        <input type="radio" name="mode" value={m} bind:group={mode} />
        {t(`play.mode.${m}`)}
      </label>
    {/each}
  </fieldset>

  <fieldset class="space-y-1 text-sm">
    <legend class="mb-1 font-semibold">{t("play.where")}</legend>
    {#each ["local", "online"] as const as w (w)}
      <label class="flex items-center gap-2">
        <input type="radio" name="where" value={w} bind:group={where} />
        {t(`play.${w}`)}
      </label>
    {/each}
  </fieldset>

  <table class="table">
    <thead>
      <tr>
        <th>{t("play.seat")}</th>
        <th>{t("play.team")}</th>
        <th></th>
        <th>{t("play.name")}</th>
        <th>{t("play.bot")}</th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row, i (i)}
        <tr>
          <td>{i + 1}</td>
          <td class={i % 2 ? "text-rose-700" : "text-indigo-700"}>
            {(i % 2) + 1} · {t("play.number")}
            {Math.floor((i % 2 ? (i + 3) % 6 : i) / 2) + 1}
          </td>
          <td>
            <select class="input" name="kind-{i}" bind:value={row.kind}>
              <option value="human">{t("play.human")}</option>
              <option value="bot">{t("play.bot")}</option>
            </select>
          </td>
          <td><input class="input" name="name-{i}" maxlength="40" bind:value={row.name} /></td>
          <td>
            {#if row.kind === "bot"}
              <select class="input" name="bot-{i}" bind:value={row.bot}>
                {#each presets as p (p.key)}
                  <option value="preset:{p.key}">{p.name}</option>
                {/each}
                {#each saved as b (b.id)}
                  <option value="saved:{b.id}">{b.name}</option>
                {/each}
              </select>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>

  {#if error}<p class="text-sm text-red-600" role="alert">{error}</p>{/if}
  <button class="btn btn-primary" type="submit" disabled={busy}>{t("play.create")}</button>
</form>
