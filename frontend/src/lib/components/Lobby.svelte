<script lang="ts">
  import type { GameView } from "$lib/api/client";
  import { avatarPortrait } from "$lib/avatar/avatar";
  import { t } from "$lib/i18n.svelte";

  // The seats of a game: who has joined and is online, the link to share, joining an open
  // seat, and (for the host, who created the game) freeing a seat whose player lost it.
  let {
    view,
    mySeats,
    isHost,
    url,
    name = $bindable(""),
    onJoin,
    onReset,
  }: {
    view: GameView;
    mySeats: number[];
    isHost: boolean;
    url: string;
    name?: string;
    onJoin: (seat: number) => void;
    onReset: (seat: number) => void;
  } = $props();

  const canJoin = $derived(!mySeats.length);
  let copied = $state(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      copied = true;
      setTimeout(() => (copied = false), 2000);
    } catch {
      copied = false; // no clipboard access: the link stays selectable
    }
  }
</script>

<section class="theme-table table-panel mx-auto mb-4 max-w-2xl space-y-4 rounded-2xl p-5">
  <h1 class="text-xl font-black tracking-wide text-amber-200">
    {view.started ? t("game.joinTitle") : t("game.waiting")}
  </h1>

  {#if !view.started}
    <div class="space-y-1 text-sm">
      <p>{t("game.share")}</p>
      <div class="flex gap-2">
        <input class="input flex-1 font-mono text-xs" readonly value={url} aria-label="URL" />
        <button class="btn" onclick={copy}>{copied ? t("game.copied") : t("game.copyLink")}</button>
      </div>
    </div>
  {/if}

  {#if canJoin}
    <input class="input max-w-xs" placeholder={t("play.name")} bind:value={name} />
  {/if}

  <ul class="grid gap-2 sm:grid-cols-2">
    {#each view.seats as s (s.seat)}
      <li class="flex items-center gap-3 rounded-xl bg-black/20 p-2" data-seat={s.seat}>
        <img src={avatarPortrait(s.character)} alt="" class="h-10 w-10 rounded-full" />
        <div class="min-w-0 flex-1">
          <p class="truncate font-semibold">
            {s.name}
            {#if mySeats.includes(s.seat)}<span class="text-amber-300">· {t("game.you")}</span>{/if}
          </p>
          <p class="text-xs text-slate-400">
            {view.team_names[s.team]} ·
            {#if s.kind === "bot"}
              Bot
            {:else if !s.joined}
              {t("game.seatOpen")}
            {:else if s.online}
              <span class="text-emerald-400">{t("game.online")}</span>
            {:else}
              <span class="text-red-400">{t("game.away")}</span>
            {/if}
          </p>
        </div>
        {#if s.kind === "human" && !s.joined && canJoin}
          <button class="btn btn-primary" onclick={() => onJoin(s.seat)}>{t("game.join")}</button>
        {:else if isHost && s.kind === "human" && s.joined && !mySeats.includes(s.seat)}
          <button class="btn" title={t("game.resetHint")} onclick={() => onReset(s.seat)}>
            {t("game.resetSeat")}
          </button>
        {/if}
      </li>
    {/each}
  </ul>

  {#if canJoin && !view.seats.some((s) => s.kind === "human" && !s.joined)}
    <p class="text-sm text-slate-400">{t("game.noSeats")}</p>
  {/if}
</section>
