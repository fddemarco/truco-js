<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import {
    api,
    errorMessage,
    type BotConfig,
    type BotPreset,
    type RuleMode,
    type SeatSetup,
  } from "$lib/api/client";
  import { CHARACTER_NAMES, CHARACTERS, type Character } from "$lib/avatar/avatar";
  import { drawTeamNames, saveToken } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import { profile } from "$lib/profile.svelte";

  let presets = $state<BotPreset[]>([]);
  let saved = $state<BotConfig[]>([]);
  let mode = $state<RuleMode>("strict");
  // The home page links here with ?where=online or ?where=local.
  let where = $state<"local" | "online">(
    page.url.searchParams.get("where") === "online" ? "online" : "local",
  );
  let error = $state<string | null>(null);
  let busy = $state(false);

  interface Row {
    kind: "human" | "bot";
    name: string;
    character: Character | ""; // "" = automatic
    bot: string; // "preset:<key>" or "saved:<id>"
  }
  // Seat 1 is this player, with their profile; bots play as their character by default.
  let rows = $state<Row[]>(
    Array.from({ length: 6 }, (_, i) => ({
      kind: i === 0 ? "human" : "bot",
      name: i === 0 ? profile.name : "",
      character: i === 0 ? profile.character : "",
      bot: "preset:prolijo",
    })),
  );
  let teamNames = $state<[string, string]>(drawTeamNames());
  /** Characters picked by another row, not offered again. */
  const takenBy = (i: number) =>
    rows.flatMap((r, j) => (j !== i && r.character ? [r.character] : []));

  onMount(async () => {
    const [p, b] = await Promise.all([api.GET("/api/bots/presets"), api.GET("/api/bots")]);
    presets = p.data ?? [];
    saved = b.data ?? [];
  });

  const humans = $derived(rows.flatMap((r, i) => (r.kind === "human" ? [i] : [])));

  function setup(row: Row): SeatSetup {
    const character = row.character || null;
    if (row.kind === "human") {
      return { kind: "human", name: row.name, character, bot_id: null, bot_preset: null };
    }
    const [kind, id] = row.bot.split(":");
    return kind === "saved"
      ? { kind: "bot", name: row.name, character, bot_id: Number(id), bot_preset: null }
      : { kind: "bot", name: row.name, character, bot_preset: id, bot_id: null };
  }

  async function start(event: SubmitEvent) {
    event.preventDefault();
    if (!humans.length) {
      error = t("play.needHuman");
      return;
    }
    busy = true;
    error = null;
    const names = teamNames.map((n) => n.trim());
    const created = await api.POST("/api/games", {
      body: { mode, seats: rows.map(setup), team_names: names.every(Boolean) ? names : null },
    });
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

  <fieldset class="text-sm">
    <legend class="mb-1 font-semibold">{t("play.teamNames")}</legend>
    <div class="flex flex-wrap items-center gap-2">
      {#each [0, 1] as team (team)}
        <input
          class="input max-w-52 border-2 {team ? 'border-rose-300' : 'border-indigo-300'}"
          name="team-{team}"
          maxlength="24"
          bind:value={teamNames[team]}
        />
      {/each}
      <button
        type="button"
        class="btn"
        title={t("play.drawNames")}
        aria-label={t("play.drawNames")}
        onclick={() => (teamNames = drawTeamNames(Math.random, teamNames))}>🎲</button
      >
    </div>
  </fieldset>

  <table class="table">
    <thead>
      <tr>
        <th>{t("play.seat")}</th>
        <th>{t("play.team")}</th>
        <th></th>
        <th>{t("play.name")}</th>
        <th>{t("play.character")}</th>
        <th>{t("play.bot")}</th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row, i (i)}
        <tr>
          <td>{i + 1}</td>
          <td class={i % 2 ? "text-rose-700" : "text-indigo-700"}>
            {teamNames[i % 2]} · {t("play.number")}
            {Math.floor((i % 2 ? (i + 3) % 6 : i) / 2) + 1}
          </td>
          <td>
            <select class="input" name="kind-{i}" bind:value={row.kind}>
              <option value="human">{t("play.human")}</option>
              <option value="bot">{t("play.bot")}</option>
            </select>
          </td>
          <td>
            <input
              class="input"
              name="name-{i}"
              maxlength="40"
              placeholder={row.kind === "bot" && row.character
                ? CHARACTER_NAMES[row.character]
                : ""}
              bind:value={row.name}
            />
          </td>
          <td>
            <select class="input" name="character-{i}" bind:value={row.character}>
              <option value="">{t("play.anyCharacter")}</option>
              {#each CHARACTERS as c (c)}
                <option value={c} disabled={takenBy(i).includes(c)}>{CHARACTER_NAMES[c]}</option>
              {/each}
            </select>
          </td>
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
