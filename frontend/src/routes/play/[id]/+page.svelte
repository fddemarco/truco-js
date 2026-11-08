<script lang="ts">
  import { onMount, untrack } from "svelte";
  import {
    applyBeats,
    BeatQueue,
    beats,
    isNewer,
    newEvents,
    rewind,
    type Beat,
  } from "$lib/animation";
  import { page } from "$app/state";
  import { api, errorMessage, type GameAction, type GameView } from "$lib/api/client";
  import type { BodySpot, Sena } from "$lib/avatar/avatar";
  import GameTable from "$lib/components/GameTable.svelte";
  import { loadTokens, nextDeal, saveToken } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import { play, sfxFor, startMusic, stopMusic, syncMusicVolume } from "$lib/audio.svelte";
  import { log } from "$lib/log";
  import { profile } from "$lib/profile.svelte";

  const POLL_MS = 1000;
  const gameId = page.params.id ?? "";

  let tokens = $state<Record<number, string>>(loadTokens(gameId));
  const mySeats = $derived(Object.keys(tokens).map(Number).sort());
  let seat = $state<number | null>(null); // the seat this device is acting as
  let revealed = $state(true);
  // `latest` is what the server sent; `view` is what the table shows. Moves since then play
  // as beats (1-2 s for a bot) before the table catches up (see $lib/animation).
  let latest = $state.raw<GameView | null>(null);
  let view = $state<GameView | null>(null);
  let beat = $state<Beat | null>(null);
  let landed = $state<Beat[]>([]);
  let settled = $state(0);
  let look = $state<number | null>(null); // the player across the camera is on
  const queue = new BeatQueue(
    (b, done) => {
      log.debug("beat.start", {
        game_id: gameId,
        beat: b.id,
        kind: b.kind,
        seat: b.seat,
        ms: b.ms,
        think: b.think,
        done: done.length,
      });
      beat = b;
      landed = [...done, b];
      const sound = sfxFor(b.kind);
      if (sound) setTimeout(() => beat?.id === b.id && play(sound), b.think);
      // The move enters the log (and scores) once the player has finished thinking.
      settled = done.length;
      if (b.think) setTimeout(() => beat?.id === b.id && (settled = done.length + 1), b.think);
      else settled = done.length + 1;
    },
    () => {
      log.debug("beat.idle", { game_id: gameId, version: latest?.version });
      beat = null;
      landed = [];
      if (latest) settle(latest);
    },
  );
  const busy = $derived(beat !== null);
  // While beats play, the table is the old view with the cards played so far landed on it
  // (señas stay live).
  const display = $derived(
    view && busy && latest ? { ...applyBeats(view, landed, settled), senas: latest.senas } : view,
  );
  let offset = $state(0);
  let error = $state<string | null>(null);
  let joinName = $state(profile.name);

  const token = $derived(seat !== null ? tokens[seat] : undefined);
  const local = $derived(mySeats.length > 1);
  const openSeats = $derived(view?.seats.filter((s) => s.kind === "human" && !s.joined) ?? []);

  function show(next: GameView) {
    offset = next.server_ms - Date.now();
    if (!isNewer(latest, next)) {
      // Same version: only señas may have changed. Older: a stale response, dropped.
      if (latest && next.version === latest.version) {
        latest = { ...latest, senas: next.senas };
        if (!queue.busy) settle(latest);
      } else
        log.debug("game.view_stale", {
          game_id: gameId,
          version: next.version,
          latest: latest?.version,
        });
      return;
    }
    const bots = new Set(next.seats.filter((s) => s.kind === "bot").map((s) => s.seat));
    let fresh = latest ? newEvents(latest.events, next.events) : [];
    if (!latest) {
      // Arriving at the table: replay what happened since our last move (or the deal),
      // instead of showing it all at once.
      const back = rewind(next);
      if (back.replay.length) {
        view = back.view;
        fresh = back.replay;
      }
    }
    const moves = beats(fresh, bots);
    if (latest && next.version !== latest.version) {
      log.debug("game.view", {
        game_id: gameId,
        seat,
        version: next.version,
        events: next.events.length,
        new_events: fresh.length,
        beats: moves.length,
        busy: queue.busy,
      });
    }
    latest = next;
    if (moves.length) queue.push(moves);
    else if (!queue.busy) settle(next);
  }

  function fail(err: unknown) {
    error = errorMessage(err);
    log.warn("game.error", { game_id: gameId, seat, message: error });
  }

  function settle(next: GameView) {
    if (view?.version !== next.version) {
      log.debug("game.settled", { game_id: gameId, version: next.version, to_act: next.to_act });
    }
    view = next;
    // Local multiplayer: follow the turn to the next human on this device, behind a curtain.
    const turn = next.to_act;
    if (turn !== null && turn !== undefined && turn in tokens && turn !== seat) {
      seat = turn;
      if (local) revealed = false;
    }
  }

  async function refresh() {
    const res = await api.GET("/api/games/{game_id}", {
      params: { path: { game_id: gameId }, query: { token: token ?? null, look } },
    });
    if (res.data) {
      show(res.data);
    } else fail(res.error);
  }

  onMount(() => {
    seat = mySeats[0] ?? null;
    refresh();
    const id = setInterval(refresh, POLL_MS);
    // Browsers only allow sound after a gesture: the music starts with the first one.
    const start = () => startMusic();
    window.addEventListener("pointerdown", start, { once: true });
    window.addEventListener("keydown", start, { once: true });
    return () => {
      clearInterval(id);
      queue.stop();
      window.removeEventListener("pointerdown", start);
      window.removeEventListener("keydown", start);
      stopMusic();
    };
  });

  $effect(syncMusicVolume);

  async function act(action: GameAction) {
    if (!token) return;
    log.info("game.act", {
      game_id: gameId,
      seat,
      kind: action.kind,
      card: action.card ? `${action.card.number}-${action.card.suit}` : null,
      number: action.number,
    });
    const res = await api.POST("/api/games/{game_id}/act", {
      params: { path: { game_id: gameId } },
      body: { token, action, look },
    });
    if (res.data) {
      error = null;
      show(res.data);
    } else fail(res.error);
  }

  // --- between manos: shuffle, cut, deal (no button to press) -----------------------------
  const plan = $derived(view && !busy ? nextDeal(view, mySeats) : null);
  let dealAt = $state<{ version: number; endsAt: number } | null>(null);
  let cutting = $state(false);
  // Polling hands over a fresh view object each second: only a new version restarts the wait.
  const planKey = $derived(
    plan && view ? `${view.version}:${plan.cutter}:${plan.mine}:${plan.waitMs}` : null,
  );
  $effect(() => {
    if (!planKey) {
      dealAt = null;
      return;
    }
    const p = untrack(() => plan);
    if (!p) return;
    const endsAt = Date.now() + p.waitMs;
    dealAt = { version: untrack(() => view?.version ?? 0), endsAt };
    play("shuffle");
    const timer = setTimeout(() => (p.mine ? cut() : deal(p.cutter)), p.waitMs);
    return () => clearTimeout(timer);
  });

  function cut() {
    if (cutting || !plan) return;
    const cutter = plan.cutter;
    cutting = true;
    play("cut");
    log.info("game.cut", { game_id: gameId, seat: cutter });
    setTimeout(() => {
      cutting = false;
      deal(cutter);
    }, 700);
  }

  async function deal(cutter: number) {
    // Deal from the cutter's token when it's ours, else from whichever seat we hold.
    const from = tokens[cutter] ?? token ?? Object.values(tokens)[0];
    if (!from) return;
    log.info("game.deal", { game_id: gameId, seat: cutter });
    const res = await api.POST("/api/games/{game_id}/deal", {
      params: { path: { game_id: gameId } },
      body: { token: from, look },
    });
    if (res.data) show(res.data);
    // Online, another device may have dealt first: the next poll shows the new mano.
    else if (res.response.status !== 400) fail(res.error);
  }

  async function sena(s: Sena, spot: BodySpot, durationMs: number) {
    if (!token) return;
    const res = await api.POST("/api/games/{game_id}/sena", {
      params: { path: { game_id: gameId } },
      body: { token, sena: s, spot, duration_ms: durationMs, target: null, look },
    });
    if (res.data) show(res.data);
    else fail(res.error);
  }

  async function join(target: number) {
    const res = await api.POST("/api/games/{game_id}/join", {
      params: { path: { game_id: gameId } },
      body: { seat: target, name: joinName },
    });
    if (!res.data) {
      fail(res.error);
      return;
    }
    saveToken(gameId, target, res.data.token);
    tokens = loadTokens(gameId);
    seat = target;
    await refresh();
  }

  function choose(next: number) {
    seat = next;
    revealed = !local;
    refresh();
  }
</script>

{#if error}<p class="mb-3 text-sm text-red-600" role="alert">{error}</p>{/if}

{#if view}
  {#if !mySeats.length}
    <section class="card mb-4 space-y-2">
      {#if openSeats.length}
        <h1 class="font-semibold">{t("game.joinTitle")}</h1>
        <input class="input max-w-xs" placeholder={t("play.name")} bind:value={joinName} />
        <div class="flex flex-wrap gap-2">
          {#each openSeats as s (s.seat)}
            <button class="btn" onclick={() => join(s.seat)}>
              {t("game.join")}: {s.name} · {view.team_names[s.team]}
            </button>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-slate-600">{t("game.noSeats")}</p>
      {/if}
    </section>
  {/if}

  {#if !view.started}
    <section class="card mb-4 text-sm">
      <p>{t("game.waiting")}</p>
      <p class="mt-1">{t("game.share")}</p>
      <code class="mt-1 block rounded bg-slate-100 p-2">{page.url.href}</code>
    </section>
  {/if}

  {#if local}
    <div class="mb-3 flex items-center gap-2 text-sm">
      <span class="font-semibold">{t("game.mySeats")}:</span>
      {#each mySeats as s (s)}
        <button class="btn {s === seat ? 'btn-primary' : ''}" onclick={() => choose(s)}>
          {view.seats[s].name}
        </button>
      {/each}
    </div>
  {/if}

  {#if seat !== null && !revealed}
    <!-- Hot-seat curtain: hide the previous player's cards until the next one is ready. -->
    <section class="card flex flex-col items-center gap-3 py-16 text-center" role="dialog">
      <p class="text-xl font-semibold">{t("game.turnOf", { name: view.seats[seat].name })}</p>
      <p class="text-sm text-slate-600">
        {t("game.passDevice", { name: view.seats[seat].name })}
      </p>
      <button class="btn btn-primary" onclick={() => (revealed = true)}>{t("game.reveal")}</button>
    </section>
  {:else}
    <GameTable
      view={display ?? view}
      viewer={seat ?? 0}
      {offset}
      {beat}
      {busy}
      onAct={act}
      nextDeal={plan && dealAt
        ? { cutter: plan.cutter, mine: plan.mine, endsAt: dealAt.endsAt }
        : null}
      {cutting}
      onCut={cut}
      onSena={view.mode === "interactive" ? sena : undefined}
      onLook={(s) => {
        look = s;
        refresh();
      }}
    />
  {/if}
{/if}
