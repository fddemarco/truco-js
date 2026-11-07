<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { api, errorMessage, type GameAction, type GameView } from "$lib/api/client";
  import type { BodySpot, Sena } from "$lib/avatar/avatar";
  import GameTable from "$lib/components/GameTable.svelte";
  import { loadTokens, saveToken } from "$lib/game";
  import { t } from "$lib/i18n.svelte";

  const POLL_MS = 1000;
  const gameId = page.params.id ?? "";

  let tokens = $state<Record<number, string>>(loadTokens(gameId));
  const mySeats = $derived(Object.keys(tokens).map(Number).sort());
  let seat = $state<number | null>(null); // the seat this device is acting as
  let revealed = $state(true);
  let view = $state<GameView | null>(null);
  let offset = $state(0);
  let error = $state<string | null>(null);
  let joinName = $state("");

  const token = $derived(seat !== null ? tokens[seat] : undefined);
  const local = $derived(mySeats.length > 1);
  const openSeats = $derived(view?.seats.filter((s) => s.kind === "human" && !s.joined) ?? []);

  function show(next: GameView) {
    view = next;
    offset = next.server_ms - Date.now();
    // Local multiplayer: follow the turn to the next human on this device, behind a curtain.
    const turn = next.to_act;
    if (turn !== null && turn !== undefined && turn in tokens && turn !== seat) {
      seat = turn;
      if (local) revealed = false;
    }
  }

  async function refresh() {
    const res = await api.GET("/api/games/{game_id}", {
      params: { path: { game_id: gameId }, query: { token: token ?? null } },
    });
    if (res.data) {
      if (!view || res.data.version !== view.version || res.data.senas.length) show(res.data);
    } else error = errorMessage(res.error);
  }

  onMount(() => {
    seat = mySeats[0] ?? null;
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  });

  async function act(action: GameAction) {
    if (!token) return;
    const res = await api.POST("/api/games/{game_id}/act", {
      params: { path: { game_id: gameId } },
      body: { token, action },
    });
    if (res.data) {
      error = null;
      show(res.data);
    } else error = errorMessage(res.error);
  }

  async function deal() {
    if (!token) return;
    const res = await api.POST("/api/games/{game_id}/deal", {
      params: { path: { game_id: gameId } },
      body: { token },
    });
    if (res.data) show(res.data);
    else error = errorMessage(res.error);
  }

  async function sena(s: Sena, spot: BodySpot, durationMs: number) {
    if (!token) return;
    const res = await api.POST("/api/games/{game_id}/sena", {
      params: { path: { game_id: gameId } },
      body: { token, sena: s, spot, duration_ms: durationMs, target: null },
    });
    if (res.data) show(res.data);
    else error = errorMessage(res.error);
  }

  async function join(target: number) {
    const res = await api.POST("/api/games/{game_id}/join", {
      params: { path: { game_id: gameId } },
      body: { seat: target, name: joinName },
    });
    if (!res.data) {
      error = errorMessage(res.error);
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
              {t("game.join")}: {s.name} · {t("game.team", { n: s.team + 1 })}
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
      {view}
      viewer={seat ?? 0}
      {offset}
      onAct={act}
      onDeal={deal}
      onSena={view.mode === "interactive" ? sena : undefined}
    />
  {/if}
{/if}
