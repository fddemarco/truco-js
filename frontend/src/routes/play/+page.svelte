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
    type ScoringInfo,
    type SeatSetup,
  } from "$lib/api/client";
  import { avatarPortrait, CHARACTER_NAMES, CHARACTERS, type Character } from "$lib/avatar/avatar";
  import BotManager from "$lib/components/BotManager.svelte";
  import ScoringEditor from "$lib/components/ScoringEditor.svelte";
  import { drawTeamNames, saveToken } from "$lib/game";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import { profile, updateProfile } from "$lib/profile.svelte";
  import { scoringSetup } from "$lib/scoring";

  // Everything about a game is set here, before it starts: seats, scoring and the bots
  // themselves. None of it can change during a game.
  const TABS = ["game", "points", "bots"] as const;
  type Tab = (typeof TABS)[number];
  let tab = $state<Tab>(TABS.find((x) => x === page.url.searchParams.get("tab")) ?? "game");
  let scoringInfo = $state<ScoringInfo | null>(null);

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

  async function loadSaved() {
    saved = (await api.GET("/api/bots")).data ?? [];
    // A deleted saved bot can't stay on a seat: back to the default preset.
    for (const row of rows)
      if (row.bot.startsWith("saved:") && !saved.some((b) => `saved:${b.id}` === row.bot))
        row.bot = "preset:prolijo";
  }

  onMount(async () => {
    const [p, sc] = await Promise.all([
      api.GET("/api/bots/presets"),
      api.GET("/api/games/scoring"),
      loadSaved(),
    ]);
    presets = p.data ?? [];
    scoringInfo = sc.data ?? null;
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

  async function start(event: Event) {
    event.preventDefault();
    if (!humans.length) {
      error = t("play.needHuman");
      return;
    }
    // The table plays full screen: browsers only allow it from a click, so ask now.
    document.documentElement.requestFullscreen?.().catch(() => {});
    busy = true;
    error = null;
    const names = teamNames.map((n) => n.trim());
    const created = await api.POST("/api/games", {
      body: {
        mode,
        seats: rows.map(setup),
        team_names: names.every(Boolean) ? names : null,
        scoring: scoringSetup(profile.scoring),
      },
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

<section class="theme-table table-panel space-y-5 rounded-2xl p-5">
  <div class="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 class="text-2xl font-black tracking-wide text-amber-200">{t("play.title")}</h1>
      <p class="mt-1 text-sm text-amber-100/70">{t("play.intro")}</p>
    </div>
    <span class="rounded-full bg-black/30 px-3 py-1 text-xs font-semibold text-amber-100/80">
      {t("play.summary", { target: profile.scoring.target })}
    </span>
  </div>

  <div class="flex gap-1 border-b border-amber-100/15" role="tablist">
    {#each TABS as id (id)}
      <button
        type="button"
        role="tab"
        aria-selected={tab === id}
        class="-mb-px border-b-2 px-4 py-2 text-sm font-bold {tab === id
          ? 'border-amber-400 text-amber-200'
          : 'border-transparent text-amber-100/60 hover:text-amber-50'}"
        onclick={() => (tab = id)}>{t(`play.tab.${id}` as MessageKey)}</button
      >
    {/each}
  </div>

  {#if tab === "points"}
    {#if scoringInfo}
      <ScoringEditor
        info={scoringInfo}
        value={profile.scoring}
        onChange={(scoring) => updateProfile({ scoring })}
      />
    {:else}
      <p class="text-sm text-amber-100/70">…</p>
    {/if}
  {:else if tab === "bots"}
    <BotManager onChange={loadSaved} />
  {:else}
    <form class="space-y-5" onsubmit={start}>
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
              class="input max-w-52 border-2 {team ? 'border-rose-400/70' : 'border-[#818cf8]/70'}"
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
            <th><span class="sr-only">{t("play.character")}</span></th>
            <th></th>
            <th>{t("play.name")}</th>
            <th>{t("play.character")}</th>
            <th>{t("play.bot")}</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row, i (i)}
            <tr class={i % 2 ? "bg-rose-400/10" : "bg-[#818cf8]/10"} title={teamNames[i % 2]}>
              <td
                class="border-l-4 font-semibold {i % 2
                  ? 'border-l-rose-400 text-rose-200'
                  : 'border-l-[#818cf8] text-[#c7d2fe]'}"
              >
                {i + 1}
              </td>
              <td>
                <!-- the character's face (a "?" until one is picked), a robot for a bot -->
                <div class="relative h-11 w-11" data-testid="seat-face-{i}">
                  {#if row.character}
                    <img
                      class="h-11 w-11 rounded-full bg-black/20 object-cover ring-2 ring-amber-100/30"
                      src={avatarPortrait(row.character)}
                      alt={CHARACTER_NAMES[row.character]}
                    />
                  {:else}
                    <span
                      class="flex h-11 w-11 items-center justify-center rounded-full border-2 border-dashed border-amber-100/30 text-lg font-bold text-amber-100/50"
                      aria-label={t("play.anyCharacter")}>?</span
                    >
                  {/if}
                  {#if row.kind === "bot"}
                    <span
                      class="absolute -right-1 -bottom-1 flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-amber-200 ring-2 ring-slate-950"
                      title={t("play.bot")}
                      data-testid="seat-bot-{i}"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        aria-label={t("play.bot")}
                        role="img"
                        ><path d="M12 8V4H8" /><rect
                          width="16"
                          height="12"
                          x="4"
                          y="8"
                          rx="2"
                        /><path d="M2 14h2M20 14h2M15 13v2M9 13v2" /></svg
                      >
                    </span>
                  {/if}
                </div>
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
                    <option value={c} disabled={takenBy(i).includes(c)}>{CHARACTER_NAMES[c]}</option
                    >
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
    </form>
  {/if}

  <!-- Starting is always at hand, whichever tab is open. -->
  <div class="flex items-center gap-3 border-t border-amber-100/15 pt-4">
    <button
      class="rounded-xl bg-amber-400 px-6 py-2.5 text-base font-black text-amber-950 shadow-lg transition hover:-translate-y-0.5 hover:bg-amber-300 disabled:opacity-50"
      type="button"
      disabled={busy}
      onclick={start}>{t("play.create")}</button
    >
    {#if error}<p class="text-sm text-red-300" role="alert">{error}</p>{/if}
  </div>
</section>
