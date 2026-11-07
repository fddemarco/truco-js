<script lang="ts">
  import { onMount } from "svelte";
  import type { GameAction, GameEvent, GameView } from "$lib/api/client";
  import type { BodySpot, Sena } from "$lib/avatar/avatar";
  import { cardName, type Suit } from "$lib/cards";
  import {
    ACTION_LABELS,
    actionLabel,
    activeSenas,
    buttonActions,
    canPlay,
    seatPosition,
    senaForCode,
    type SeatPosition,
  } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";
  import PlayingCard from "./PlayingCard.svelte";

  interface Props {
    view: GameView;
    /** The seat drawn at the bottom: the viewer's, or seat 0 for spectators. */
    viewer: number;
    /** server clock − local clock, to time señas. */
    offset?: number;
    onAct: (action: GameAction) => void;
    onDeal: () => void;
    onSena?: (sena: Sena, spot: BodySpot, durationMs: number) => void;
  }

  let { view, viewer, offset = 0, onAct, onDeal, onSena }: Props = $props();

  let now = $state(Date.now());
  onMount(() => {
    const id = setInterval(() => (now = Date.now()), 150);
    return () => clearInterval(id);
  });

  const senas = $derived(activeSenas(view.senas, now + offset));
  const ronda = $derived(view.rounds.at(-1) ?? []);
  const declarations = $derived(view.actions.filter((a) => a.kind === "declarar"));
  const strictSenas = $derived(view.actions.filter((a) => a.kind === "sena"));
  const buttons = $derived(buttonActions(view.actions));

  const PLACE: Record<SeatPosition, string> = {
    bottom: "left-1/2 bottom-0 -translate-x-1/2",
    "bottom-right": "right-[4%] bottom-[18%]",
    "top-right": "right-[12%] top-0",
    top: "left-1/2 top-0 -translate-x-1/2 scale-90",
    "top-left": "left-[12%] top-0",
    "bottom-left": "left-[4%] bottom-[18%]",
  };
  const FAR = new Set<SeatPosition>(["top-right", "top", "top-left"]);

  function played(seat: number) {
    return ronda.find((p) => p.seat === seat)?.card;
  }

  function describe(e: GameEvent): string {
    const who = e.seat != null ? view.seats[e.seat].name : "";
    switch (e.kind) {
      case "reparto":
        return `— ${t("game.handNumber", { n: e.number ?? "" })} —`;
      case "fin_mano":
        return `${t("game.endMano")}: ${e.points?.join("–")}`;
      case "resultado":
        return `${e.points?.join("–")}`;
      case "envido_resuelto":
        return `${who} ${t("game.envidoWon")} (${Math.max(...(e.points ?? [0]))})`;
      case "interferencia":
        return `${who}: ${t("game.interference")}`;
      case "jugar":
        return e.card ? `${who}: ${cardName(e.card.number, e.card.suit as Suit)}` : who;
      case "declarar":
        return `${who}: ${e.number}`;
      case "reclamar":
        return `${who}: ${ACTION_LABELS.reclamar} (${t(e.upheld ? "game.claimUpheld" : "game.claimRejected")})`;
      default:
        return `${who}: ${ACTION_LABELS[e.kind as keyof typeof ACTION_LABELS] ?? e.kind}`;
    }
  }

  // Interactive señas: hold a key, release to send with the held time as duration.
  const held = new Map<string, number>();
  function typing(target: EventTarget | null) {
    return (
      target instanceof HTMLElement && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)
    );
  }
  function keydown(e: KeyboardEvent) {
    if (!onSena || view.mode !== "interactive" || e.repeat || typing(e.target)) return;
    if (senaForCode(e.code, e.shiftKey)) held.set(e.code, Date.now());
  }
  function keyup(e: KeyboardEvent) {
    const start = held.get(e.code);
    held.delete(e.code);
    const sena = senaForCode(e.code, e.shiftKey);
    if (start === undefined || !sena || !onSena) return;
    onSena(sena.sena, sena.spot, Math.min(5000, Math.max(150, Date.now() - start)));
  }
</script>

<svelte:window onkeydown={keydown} onkeyup={keyup} />

<div class="grid gap-4 lg:grid-cols-[1fr_16rem]">
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-4 text-sm">
      {#each [0, 1] as team (team)}
        <div class="rounded-md border border-slate-200 bg-white px-3 py-1">
          <span class="font-semibold">{t("game.team", { n: team + 1 })}</span>
          <span class="ml-2 font-mono text-lg" data-testid="score-{team}">{view.score[team]}</span>
          <span class="ml-1 text-xs text-slate-500"
            >{view.score[team] > 15 ? "buenas" : "malas"}</span
          >
        </div>
      {/each}
      {#if view.hand_kind}
        <span class="rounded bg-slate-100 px-2 py-1">
          {t("game.handNumber", { n: view.hand_number })} ·
          {view.hand_kind === "pica_pica" ? "Pica-pica" : "Mano redonda"}
        </span>
      {/if}
      {#if view.truco_accepted > 0}
        <span class="rounded bg-amber-100 px-2 py-1">
          {["", "Truco", "Retruco", "Vale cuatro"][view.truco_accepted]}
        </span>
      {/if}
    </div>

    <!-- The felt is tilted away for depth; seats stay upright, farther ones smaller. -->
    <div class="relative h-[26rem] [perspective:900px]">
      <div
        class="absolute inset-x-[6%] inset-y-[14%] rounded-[45%] border-8 border-amber-900 bg-green-700 shadow-inner [transform:rotateX(28deg)]"
      ></div>
      {#each view.seats as seat (seat.seat)}
        {@const pos = seatPosition(seat.seat, viewer)}
        {@const card = played(seat.seat)}
        {@const sena = senas.get(seat.seat)}
        <div
          class="absolute flex flex-col items-center gap-1 {PLACE[pos]} {FAR.has(pos)
            ? 'opacity-95'
            : ''}"
          data-testid="seat-{seat.seat}"
        >
          <div
            class="relative rounded-full p-1 {view.to_act === seat.seat
              ? 'ring-4 ring-amber-400'
              : ''} {seat.in_play && !seat.active ? 'opacity-40' : ''}"
          >
            <Avatar
              look={seat.seat}
              label={seat.name}
              sena={sena?.sena}
              spot={sena?.spot}
              class={FAR.has(pos) ? "w-16" : "w-20"}
            />
          </div>
          <div class="flex items-center gap-1 rounded bg-white/90 px-2 text-xs shadow">
            <span class="font-semibold {seat.team === 0 ? 'text-indigo-700' : 'text-rose-700'}">
              {seat.name}
            </span>
            <span class="text-slate-500">#{seat.number}</span>
            {#if view.mano === seat.seat}<span class="rounded bg-slate-800 px-1 text-white"
                >mano</span
              >{/if}
            {#if seat.in_play && !seat.active}<span class="text-slate-500">· {t("game.out")}</span
              >{/if}
          </div>
          {#if card}
            <PlayingCard number={card.number} suit={card.suit as Suit} class="w-12 shadow-md" />
          {:else if seat.seat !== viewer && seat.cards_left > 0}
            <div class="flex -space-x-6">
              {#each Array(seat.cards_left) as _, i (i)}
                <PlayingCard faceDown class="w-8" />
              {/each}
            </div>
          {/if}
          {#if seat.shown.length}
            <div class="flex gap-1">
              {#each seat.shown as c (c.number + c.suit)}
                <PlayingCard number={c.number} suit={c.suit as Suit} class="w-8" />
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if view.result}
      <p class="card text-center text-lg font-semibold" role="status">
        {view.result.winner === null
          ? t("game.noWinner")
          : t("game.won", { n: view.result.winner + 1 })}
        {view.score.join("–")}
      </p>
    {/if}

    {#if view.me !== null}
      <div class="card space-y-3">
        <div class="flex gap-2">
          {#each view.my_cards as c (c.number + c.suit)}
            {@const playable = canPlay(view, c.number, c.suit)}
            <button
              class="rounded-lg transition hover:-translate-y-1 disabled:hover:translate-y-0"
              disabled={!playable}
              aria-label={cardName(c.number, c.suit as Suit)}
              onclick={() => onAct({ kind: "jugar", card: c, number: null, sena: null })}
            >
              <PlayingCard
                number={c.number}
                suit={c.suit as Suit}
                class="w-24 {playable ? '' : 'opacity-70'}"
              />
            </button>
          {/each}
        </div>

        {#if buttons.length}
          <div class="flex flex-wrap gap-2">
            {#each buttons as a (a.kind)}
              <button class="btn" onclick={() => onAct(a)}>{actionLabel(a)}</button>
            {/each}
          </div>
        {/if}

        {#if declarations.length}
          <div>
            <p class="mb-1 text-sm font-semibold">{t("game.declare")}</p>
            <div class="flex flex-wrap gap-1">
              {#each declarations as a (a.number)}
                <button class="btn px-2" onclick={() => onAct(a)}>{a.number}</button>
              {/each}
            </div>
          </div>
        {/if}

        {#if strictSenas.length}
          <select
            class="input max-w-xs"
            aria-label={t("game.senaPick")}
            onchange={(e) => {
              const a = strictSenas.find((s) => s.sena === e.currentTarget.value);
              if (a) onAct(a);
              e.currentTarget.value = "";
            }}
          >
            <option value="">{t("game.senaPick")}</option>
            {#each strictSenas as a (a.sena)}
              <option value={a.sena}>{a.sena?.replace("sena_", "Seña ")}</option>
            {/each}
          </select>
        {/if}
        {#if view.mode === "interactive" && onSena}
          <p class="text-xs text-slate-500">{t("game.senaHelp")}</p>
        {/if}

        {#if view.can_deal}
          <button class="btn btn-primary" onclick={onDeal}>{t("game.next")}</button>
        {/if}
      </div>
    {/if}
  </div>

  <aside class="card max-h-[40rem] space-y-3 overflow-y-auto text-sm">
    <h2 class="font-semibold">{t("game.moves")}</h2>
    <ol class="space-y-1" data-testid="events">
      {#each [...view.events].reverse() as e, i (i)}
        <li class={e.kind === "fin_mano" || e.kind === "reparto" ? "text-slate-500" : ""}>
          {describe(e)}
        </li>
      {/each}
    </ol>
    {#if view.senas_seen.length}
      <h2 class="font-semibold">{t("game.senasSeen")}</h2>
      <ul>
        {#each view.senas_seen as s, i (i)}
          <li>{view.seats[s.seat].name}: {s.sena.replace("sena_", "Seña ")}</li>
        {/each}
      </ul>
    {/if}
  </aside>
</div>
