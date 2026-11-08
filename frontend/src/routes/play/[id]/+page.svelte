<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import GameTable from "$lib/components/GameTable.svelte";
  import Lobby from "$lib/components/Lobby.svelte";
  import { TableSession } from "$lib/gameSession.svelte";
  import { t } from "$lib/i18n.svelte";
  import { play } from "$lib/audio.svelte";
  import { profile } from "$lib/profile.svelte";

  // The table: networking, beats and the deal live in TableSession; this page lays it out
  // (lobby, seat switcher, hot-seat curtain).
  const game = new TableSession(page.params.id ?? "", () => goto("/", { replaceState: true }));
  let joinName = $state(profile.name);
  onMount(() => game.start());

  // The table shuffles while it waits to deal (the server deals at `deal_at`).
  const shuffleAt = $derived(game.plan?.endsAt ?? null);
  $effect(() => {
    if (shuffleAt !== null) play("shuffle");
  });

  // During the game the host sees seats whose player is away, to free them.
  const away = $derived(
    game.host && game.view?.started
      ? game.view.seats.filter(
          (s) => s.kind === "human" && s.joined && !s.online && !game.mySeats.includes(s.seat),
        )
      : [],
  );
  const showLobby = $derived(
    game.view !== null &&
      (!game.view.started || (!game.mySeats.length && game.openSeats.length > 0)),
  );
</script>

<!-- Above the full-screen table too. -->
{#if game.error || game.offline}
  <p
    class="fixed top-3 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-red-600 px-4 py-1.5 text-sm font-semibold text-white shadow-lg"
    role="alert"
  >
    {game.error ?? t("game.offline")}
  </p>
{/if}

{#if game.view}
  {@const view = game.view}
  {#if showLobby}
    <Lobby
      {view}
      mySeats={game.mySeats}
      isHost={game.host !== null}
      url={page.url.href}
      bind:name={joinName}
      onJoin={(s) => game.join(s, joinName, profile.character)}
      onReset={(s) => game.resetSeat(s)}
    />
  {:else if !game.mySeats.length}
    <p class="mb-3 text-center text-sm text-slate-400">{t("game.noSeats")}</p>
  {/if}

  {#if away.length}
    <div
      class="theme-table table-glass fixed right-3 bottom-3 z-[55] space-y-1 rounded-xl p-3 text-sm"
    >
      {#each away as s (s.seat)}
        <p class="flex items-center gap-2">
          <span>{s.name} · <span class="text-red-400">{t("game.away")}</span></span>
          <button class="btn" title={t("game.resetHint")} onclick={() => game.resetSeat(s.seat)}>
            {t("game.resetSeat")}
          </button>
        </p>
      {/each}
    </div>
  {/if}

  {#if game.local}
    <div class="mb-3 flex items-center gap-2 text-sm">
      <span class="font-semibold">{t("game.mySeats")}:</span>
      {#each game.mySeats as s (s)}
        <button class="btn {s === game.seat ? 'btn-primary' : ''}" onclick={() => game.choose(s)}>
          {view.seats[s].name}
        </button>
      {/each}
    </div>
  {/if}

  {#if game.seat !== null && !game.revealed}
    <!-- Hot-seat curtain: hide the previous player's cards until the next one is ready. -->
    <section class="card flex flex-col items-center gap-3 py-16 text-center" role="dialog">
      <p class="text-xl font-semibold">{t("game.turnOf", { name: view.seats[game.seat].name })}</p>
      <p class="text-sm text-slate-600">
        {t("game.passDevice", { name: view.seats[game.seat].name })}
      </p>
      <button class="btn btn-primary" onclick={() => (game.revealed = true)}>
        {t("game.reveal")}
      </button>
    </section>
  {:else if view.started}
    <GameTable
      view={game.display ?? view}
      viewer={game.seat ?? 0}
      offset={game.offset}
      beat={game.beat}
      thinking={game.thinking}
      swept={game.swept}
      busy={game.busy}
      onAct={(a) => game.act(a)}
      nextDeal={game.plan}
      cutting={game.cutting}
      onCut={() => game.cut()}
      onSena={view.mode === "interactive" ? (s, spot, ms) => game.sena(s, spot, ms) : undefined}
      onLook={(s) => game.setLook(s)}
    />
  {/if}
{/if}
