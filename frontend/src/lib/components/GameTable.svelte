<script lang="ts">
  import { onMount } from "svelte";
  import type { GameAction, GameEvent, GameView } from "$lib/api/client";
  import { BANNERS, LEAVE, LOUD, type Beat } from "$lib/animation";
  import type { BodySpot, Sena } from "$lib/avatar/avatar";
  import { cardName, type Suit } from "$lib/cards";
  import {
    ACTION_LABELS,
    across,
    activeSenas,
    canPlay,
    leadingCards,
    prompt,
    type Prompt,
    seatsAcross,
    tableSide,
  } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import { actionForKey, commandForCode, keyLabel, senaForCode } from "$lib/keys";
  import { bindings } from "$lib/profile.svelte";
  import ActionBar from "./ActionBar.svelte";
  import Hand from "./Hand.svelte";
  import HelpDialog from "./HelpDialog.svelte";
  import Mazo from "./Mazo.svelte";
  import MoveLog from "./MoveLog.svelte";
  import PlayingCard from "./PlayingCard.svelte";
  import Scoreboard from "./Scoreboard.svelte";
  import SeatBadge from "./SeatBadge.svelte";
  import TableStatus from "./TableStatus.svelte";

  interface Props {
    view: GameView;
    /** The seat whose eyes the camera uses: the viewer's, or seat 0 for spectators. */
    viewer: number;
    /** server clock − local clock, to time señas. */
    offset?: number;
    /** The move being animated, if any. */
    beat?: Beat | null;
    /** Moves are still being animated: the table is behind, so nothing can be played. */
    busy?: boolean;
    onAct: (action: GameAction) => void;
    /** The next deal, between manos: who cuts, whether it's this device, when it happens. */
    nextDeal?: { cutter: number; mine: boolean; endsAt: number } | null;
    /** The cut is being animated. */
    cutting?: boolean;
    onCut?: () => void;
    onSena?: (sena: Sena, spot: BodySpot, durationMs: number) => void;
    /** The camera turned to another player across. */
    onLook?: (seat: number) => void;
  }

  let {
    view,
    viewer,
    offset = 0,
    beat = null,
    busy = false,
    onAct,
    nextDeal = null,
    cutting = false,
    onCut,
    onSena,
    onLook,
  }: Props = $props();

  let now = $state(Date.now());
  onMount(() => {
    const id = setInterval(() => (now = Date.now()), 150);
    return () => clearInterval(id);
  });

  // --- seating and camera -----------------------------------------------------------------
  // Columns are physical positions along the table, from the viewer's left to right: the
  // player across in the top row, the one on the viewer's side in the bottom row.
  const far = $derived(seatsAcross(viewer));
  const near = $derived([0, 1, 2].map((i) => 3 * tableSide(viewer) + i));
  const myTeam = $derived(view.me !== null ? view.seats[view.me].team : null);

  let focus = $state(0);
  let focusedFor = -1;
  $effect(() => {
    // A new viewer (hot-seat) looks straight across first.
    if (viewer !== focusedFor) {
      focusedFor = viewer;
      look(across(viewer));
    }
  });
  const focusIndex = $derived(Math.max(0, far.indexOf(focus)));

  function look(seat: number) {
    focus = seat;
    onLook?.(seat);
  }
  function pan(step: number) {
    const i = Math.min(2, Math.max(0, focusIndex + step));
    if (far[i] !== focus) look(far[i]);
  }

  /** Where a seat sits in the scene, in % of its width and height (for flying cards). */
  function anchor(seat: number): { x: number; y: number } {
    const top = far.indexOf(seat);
    const col = top >= 0 ? top : near.indexOf(seat);
    return { x: ((col + 0.5) * 100) / 3, y: top >= 0 ? 12 : 66 };
  }
  /** The mazo sits on the felt in front of the dealer, beside their stack. */
  const mazo = $derived.by(() => {
    const a = anchor(view.dealer);
    return { x: a.x + 11, y: a.y < 50 ? 36 : 56 };
  });

  // Señas are only seen face to face: the player across in focus (14.4). Spectators see all.
  const senas = $derived(activeSenas(view.senas, now + offset));
  function senaOf(seat: number) {
    if (view.me !== null && seat !== focus) return undefined;
    return senas.get(seat);
  }

  function roleOf(seat: number): "mano" | "pie" | null {
    if (view.mano === seat) return "mano";
    if (view.pie === seat) return "pie";
    return null;
  }

  // --- what is going on ----------------------------------------------------------------------
  const hint = $derived.by((): Prompt => {
    if (!busy) return prompt(view);
    // While moves replay, the table shows what is happening, not what to do yet.
    if (beat?.seat != null && !BANNERS.has(beat.kind)) {
      return { tone: "wait", key: "game.prompt.watching", vars: { name: nameOf(beat.seat) } };
    }
    return { tone: "wait", key: "game.prompt.idle" };
  });
  const myTurn = $derived(!busy && view.actions.some((a) => a.kind === "jugar"));

  // The card winning the ronda being played (the ronda closes once everyone has played).
  const current = $derived(view.rounds.length > view.results.length ? view.rounds.at(-1) : null);
  const leading = $derived(
    current ? leadingCards(current, (s) => view.seats[s].team) : { seats: [], tie: false },
  );
  function leads(seat: number): "lead" | "tie" | null {
    if (!current?.some((p) => p.seat === seat) || !leading.seats.includes(seat)) return null;
    return leading.tie ? "tie" : "lead";
  }

  function nameOf(seat: number | null | undefined) {
    if (seat == null) return "";
    return seat === view.me ? t("game.you") : view.seats[seat].name;
  }

  /** An event in words. `withName: false` leaves out who did it, for the log's avatars. */
  function describe(e: GameEvent | Beat, withName = true): string {
    const who = nameOf(e.seat);
    const by = (text: string) => (withName ? `${who}: ${text}` : text);
    switch (e.kind) {
      case "reparto":
        return `— ${t("game.handNumber", { n: e.number ?? "" })} —`;
      case "fin_mano":
        return t("game.manoPoints", {
          ta: view.team_names[0],
          tb: view.team_names[1],
          a: e.points?.[0] ?? 0,
          b: e.points?.[1] ?? 0,
        });
      case "resultado":
        return `${e.points?.join("–")}`;
      case "ronda":
        if (e.seat == null) return t("game.rondaParda", { n: e.number ?? "" });
        // The viewer gets their own conjugation: "ganaste vos", not "gana Vos".
        return e.seat === view.me
          ? t("game.rondaWonMe", { n: e.number ?? "" })
          : t("game.rondaWon", { n: e.number ?? "", name: who });
      case "envido_resuelto": {
        const won = t(e.seat === view.me ? "game.envidoWonMe" : "game.envidoWon");
        return `${who} ${won} (+${Math.max(...(e.points ?? [0]))})`;
      }
      case "interferencia":
        return by(t("game.interference"));
      case "jugar":
        return e.card ? by(cardName(e.card.number, e.card.suit as Suit)) : who;
      case "declarar":
        return by(String(e.number));
      case "reclamar":
        return by(
          `${ACTION_LABELS.reclamar} (${t("upheld" in e && e.upheld ? "game.claimUpheld" : "game.claimRejected")})`,
        );
      default:
        return by(ACTION_LABELS[e.kind as keyof typeof ACTION_LABELS] ?? e.kind);
    }
  }

  /** What a player says out loud in this beat. Game terms: Spanish in every locale. */
  function said(b: Beat): string {
    if (b.kind === "declarar") return String(b.number);
    const label = ACTION_LABELS[b.kind as keyof typeof ACTION_LABELS] ?? b.kind;
    return LOUD.has(b.kind) ? `¡${label}!` : label;
  }

  // The current beat, split into what each part of the table draws.
  const speaking = $derived(
    beat && beat.seat !== null && beat.kind !== "jugar" && !BANNERS.has(beat.kind) ? beat : null,
  );
  const shout = $derived(beat && LOUD.has(beat.kind) ? beat : null);
  const banner = $derived(beat && BANNERS.has(beat.kind) ? beat : null);
  const leaving = $derived(beat && beat.seat !== null && LEAVE.has(beat.kind) ? beat : null);
  const dealing = $derived(beat?.kind === "reparto" ? beat : null);
  /** Style for the parts that wait until the player stops thinking. */
  const delay = $derived(`--think: ${beat?.think ?? 0}ms`);

  function flying(seat: number) {
    return beat?.kind === "jugar" && beat.seat === seat ? beat.id : null;
  }
  function wonRonda(seat: number) {
    return beat?.kind === "ronda" && beat.seat === seat;
  }
  function acting(seat: number) {
    return beat !== null && beat.seat === seat && !BANNERS.has(beat.kind);
  }

  // --- input ---------------------------------------------------------------------------------
  // Interactive señas: hold a key, release to send with the held time as duration.
  const held = new Map<string, number>();
  const keys = $derived(bindings());
  let helpOpen = $state(false);
  function typing(target: EventTarget | null) {
    return (
      target instanceof HTMLElement && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)
    );
  }
  function keydown(e: KeyboardEvent) {
    if (typing(e.target) || e.ctrlKey || e.metaKey || e.altKey || helpOpen) return;
    const command = commandForCode(e.code, keys);
    if (command === "cut" && nextDeal?.mine && !cutting) {
      e.preventDefault();
      onCut?.();
      return;
    }
    if (command === "look_left" || command === "look_right") {
      e.preventDefault();
      pan(command === "look_left" ? -1 : 1);
      return;
    }
    // Play and sing with the bound keys (see $lib/keys and the settings).
    const action =
      !busy && !e.repeat ? actionForKey(e.code, view.actions, view.my_cards, keys) : null;
    if (action) {
      e.preventDefault();
      onAct(action);
      return;
    }
    if (!onSena || view.mode !== "interactive" || e.repeat) return;
    if (senaForCode(e.code, keys)) {
      e.preventDefault();
      held.set(e.code, Date.now());
    }
  }
  function keyup(e: KeyboardEvent) {
    const start = held.get(e.code);
    held.delete(e.code);
    const sena = senaForCode(e.code, keys);
    if (start === undefined || !sena || !onSena) return;
    onSena(sena.sena, sena.spot, Math.min(5000, Math.max(150, Date.now() - start)));
  }

  const TEAM_BG = ["bg-indigo-500", "bg-rose-500"];
  const TONES = {
    go: "border-emerald-400 bg-emerald-50/95 text-emerald-900",
    answer: "border-amber-400 bg-amber-50/95 text-amber-950",
    wait: "border-slate-300 bg-white/90 text-slate-700",
    done: "border-indigo-400 bg-indigo-50/95 text-indigo-950",
  };
</script>

<svelte:window onkeydown={keydown} onkeyup={keyup} />

{#snippet stack(seat: number, from: "far" | "near" | "me")}
  {@const cards = view.seats[seat].played}
  {@const fly = flying(seat)}
  {@const won = wonRonda(seat)}
  {@const lead = leads(seat)}
  <div
    class="relative h-24"
    style="width: {56 + 12 * Math.max(0, cards.length - 1)}px; {delay}"
    data-testid="stack-{seat}"
  >
    {#each cards as c, i (i + c.number + c.suit)}
      {@const last = i === cards.length - 1}
      <div
        class="absolute rounded-md {fly !== null && last ? `fly fly-${from}` : ''} {won && last
          ? 'winner'
          : ''} {lead && last ? lead : ''}"
        style="left: {12 * i}px; top: {6 * i}px; z-index: {i}"
        data-lead={lead && last ? lead : undefined}
      >
        <PlayingCard number={c.number} suit={c.suit as Suit} class="w-14 shadow-md" />
        {#if lead === "lead" && last}
          <span
            class="star absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-amber-400 text-[0.7rem] text-amber-950 shadow"
            aria-hidden="true">★</span
          >
        {/if}
      </div>
    {/each}
  </div>
{/snippet}

<!-- Far players sit at the top edge of the view: their words show over their face. -->
{#snippet bubble(seat: number, place: "over" | "above")}
  {@const where = place === "over" ? "top-1/3" : "-top-9"}
  {#if beat && beat.think > 0 && beat.seat === seat}
    {#key beat.id}
      <div
        class="thinking pointer-events-none absolute left-1/2 z-30 -translate-x-1/2 rounded-full bg-white/95 px-3 py-1 text-sm font-bold text-slate-600 shadow {where}"
        style={delay}
        aria-label={t("game.thinking")}
      >
        <span class="dot">•</span><span class="dot">•</span><span class="dot">•</span>
      </div>
    {/key}
  {/if}
  {#if speaking && speaking.seat === seat}
    {#key speaking.id}
      <div
        class="say pointer-events-none absolute left-1/2 z-30 -translate-x-1/2 rounded-full px-3 py-1 font-extrabold whitespace-nowrap shadow-lg {LOUD.has(
          speaking.kind,
        )
          ? 'loud bg-amber-400 text-xl text-amber-950'
          : 'bg-white text-sm text-slate-900'} {where}"
        style={delay}
        role="status"
      >
        {said(speaking)}
      </div>
    {/key}
  {/if}
{/snippet}

<div class="grid gap-4 lg:grid-cols-[1fr_17rem]">
  <div class="space-y-3">
    <Scoreboard {view} {myTeam} {nameOf} />

    <!-- First person at a 3-3 table. The camera pans to the player across in focus. -->
    <div
      class="scene relative h-[46rem] overflow-hidden rounded-2xl shadow-2xl [perspective:1100px]"
    >
      <div
        class="camera absolute inset-0"
        style="transform: translateX({(1 - focusIndex) * 8}%) rotateY({(focusIndex - 1) * -6}deg)"
        data-focus={focus}
      >
        <div class="felt absolute inset-x-[2%] top-[22%] bottom-[24%] rounded-[3rem]"></div>

        <!-- the mazo, in front of the dealer -->
        <div
          class="absolute z-10 -translate-x-1/2 -translate-y-1/2"
          style="left: {mazo.x}%; top: {mazo.y}%"
          data-testid="mazo"
        >
          <Mazo
            class="w-11"
            state={cutting ? "cutting" : nextDeal && !busy ? "shuffling" : "idle"}
          />
          <span class="absolute -bottom-4 left-1/2 -translate-x-1/2 text-[0.6rem] text-white/80"
            >{t("game.mazo")}</span
          >
        </div>

        <div class="relative grid h-[76%] grid-cols-3">
          {#each [0, 1, 2] as col (col)}
            {@const top = far[col]}
            {@const bottom = near[col]}
            {@const ts = view.seats[top]}
            {@const bs = view.seats[bottom]}
            <div class="flex flex-col items-center justify-between pt-2">
              <!-- the player across -->
              <div class="relative flex flex-col items-center gap-1" data-testid="seat-{top}">
                {@render bubble(top, "over")}
                <SeatBadge
                  seat={ts}
                  label={nameOf(top)}
                  look={top === focus ? "focus" : "dim"}
                  size={top === focus ? "lg" : "md"}
                  mine={ts.team === myTeam}
                  role={roleOf(top)}
                  turn={view.to_act === top && !busy}
                  acting={acting(top)}
                  sena={senaOf(top)}
                  onclick={() => look(top)}
                />
                <Hand
                  cards={ts.cards_left}
                  width={34}
                  label={t("game.handOf", { name: ts.name })}
                />
                {#if ts.shown.length}
                  <div class="flex gap-1">
                    {#each ts.shown as c (c.number + c.suit)}
                      <PlayingCard number={c.number} suit={c.suit as Suit} class="w-8" />
                    {/each}
                  </div>
                {/if}
              </div>

              <!-- the played cards, each stack in front of its player -->
              <div class="flex flex-col items-center gap-2">
                {@render stack(top, "far")}
                {@render stack(bottom, bottom === viewer ? "me" : "near")}
              </div>

              <!-- the viewer's side: seen from the corner of the eye, out of focus -->
              <div class="relative flex flex-col items-center gap-1" data-testid="seat-{bottom}">
                {@render bubble(bottom, "above")}
                <SeatBadge
                  seat={bs}
                  label={nameOf(bottom)}
                  look={bottom === viewer && view.me !== null ? "focus" : "blur"}
                  size={bottom === viewer ? "md" : "sm"}
                  mine={bs.team === myTeam}
                  role={roleOf(bottom)}
                  turn={view.to_act === bottom && !busy}
                  acting={acting(bottom)}
                />
                {#if bottom !== viewer}
                  <Hand
                    cards={bs.cards_left}
                    width={26}
                    label={t("game.handOf", { name: bs.name })}
                  />
                {/if}
              </div>
            </div>
          {/each}
        </div>

        <!-- a player going to the mazo: their cards slide onto it -->
        {#if leaving && leaving.seat !== null}
          {@const from = anchor(leaving.seat)}
          {#key leaving.id}
            {#each [0, 1, 2] as i (i)}
              <div
                class="travel pointer-events-none absolute z-20"
                style="--x0: {from.x}%; --y0: {from.y}%; --x1: {mazo.x}%; --y1: {mazo.y}%; --i: {i}; {delay}"
                data-testid="to-mazo"
              >
                <PlayingCard faceDown class="w-9" />
              </div>
            {/each}
          {/key}
        {/if}

        <!-- a new deal: cards go out from the mazo to every player -->
        {#if dealing}
          {#key dealing.id}
            {#each [...far, ...near] as seat, i (seat)}
              {@const to = anchor(seat)}
              <div
                class="travel deal pointer-events-none absolute z-20"
                style="--x0: {mazo.x}%; --y0: {mazo.y}%; --x1: {to.x}%; --y1: {to.y}%; --i: {i}; --think: 0ms"
              >
                <PlayingCard faceDown class="w-8" />
              </div>
            {/each}
          {/key}
        {/if}
      </div>

      <!-- how to play, keys -->
      <button
        class="absolute top-3 right-3 z-30 rounded-full bg-white/85 p-2 text-slate-700 shadow hover:bg-white"
        aria-label={t("help.title")}
        title={t("help.title")}
        onclick={() => (helpOpen = true)}
      >
        <svg
          viewBox="0 0 24 24"
          class="h-5 w-5"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="3" />
          <path
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
          />
        </svg>
      </button>

      <!-- the state of the mano: rondas, envido, truco -->
      <div class="absolute top-3 left-3 z-20"><TableStatus {view} /></div>

      <button
        class="absolute top-[14%] left-2 z-20 rounded-full bg-white/80 px-3 py-1 text-xl shadow disabled:opacity-30"
        aria-label={t("game.lookLeft")}
        disabled={focusIndex === 0}
        onclick={() => pan(-1)}>‹</button
      >
      <button
        class="absolute top-[14%] right-2 z-20 rounded-full bg-white/80 px-3 py-1 text-xl shadow disabled:opacity-30"
        aria-label={t("game.lookRight")}
        disabled={focusIndex === 2}
        onclick={() => pan(1)}>›</button
      >

      <!-- a loud canto: the whole table hears it -->
      {#if shout && shout.seat !== null}
        {#key shout.id}
          <div
            class="shout pointer-events-none absolute top-[36%] left-1/2 z-30 -translate-x-1/2 text-center"
            style={delay}
          >
            <div class="text-5xl font-black tracking-tight text-amber-300 drop-shadow-lg">
              {said(shout)}
            </div>
            <div class="text-sm font-semibold text-white drop-shadow">{nameOf(shout.seat)}</div>
          </div>
        {/key}
      {/if}

      {#if banner}
        {#key banner.id}
          <div
            class="banner pointer-events-none absolute top-[40%] left-1/2 z-30 -translate-x-1/2 rounded-xl px-5 py-2 text-lg font-bold whitespace-nowrap text-white shadow-xl {banner.kind ===
              'ronda' && banner.seat !== null
              ? TEAM_BG[view.seats[banner.seat].team]
              : 'bg-slate-900/85'}"
            role="status"
          >
            {describe(banner)}
          </div>
        {/key}
      {/if}

      <!-- between manos: the dealer shuffles, the player to their left cuts -->
      {#if nextDeal && !busy}
        <div
          class="absolute top-[47%] left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-full bg-slate-950/80 px-4 py-2 text-sm text-white shadow-xl"
          data-testid="next-deal"
        >
          {#if nextDeal.mine}
            <span>{t("game.cutPrompt")}</span>
            <button
              class="rounded-full bg-amber-400 px-4 py-1 font-bold text-amber-950 hover:bg-amber-300 disabled:opacity-50"
              disabled={cutting}
              onclick={() => onCut?.()}
              >{t("game.cut")}
              {#if keys.cut}<kbd class="ml-1 text-xs opacity-70">{keyLabel(keys.cut)}</kbd
                >{/if}</button
            >
          {:else}
            <span>
              {t("game.nextIn", {
                s: Math.max(0, Math.ceil((nextDeal.endsAt - now) / 1000)),
                name: nameOf(nextDeal.cutter),
              })}
            </span>
          {/if}
        </div>
      {/if}

      <!-- the viewer's hand and voice, at the near edge of the table -->
      <div
        class="dock absolute inset-x-0 bottom-0 z-20 grid h-[24%] grid-cols-[1fr_auto_1fr] items-end gap-3 px-4 pb-3"
      >
        <div
          class="self-end rounded-xl border-l-4 px-3 py-2 text-sm font-semibold shadow-lg backdrop-blur {TONES[
            hint.tone
          ]}"
          role="status"
          data-testid="prompt"
          data-tone={hint.tone}
        >
          <span class="flex items-center gap-2">
            {#if hint.tone === "go" || hint.tone === "answer"}
              <span class="relative flex h-3 w-3 shrink-0">
                <span
                  class="absolute inline-flex h-full w-full animate-ping rounded-full {hint.tone ===
                  'go'
                    ? 'bg-emerald-400'
                    : 'bg-amber-400'} opacity-75"
                ></span>
                <span
                  class="relative inline-flex h-3 w-3 rounded-full {hint.tone === 'go'
                    ? 'bg-emerald-500'
                    : 'bg-amber-500'}"
                ></span>
              </span>
            {/if}
            <span>{t(hint.key, hint.vars ?? {})}</span>
            {#if view.result}<span class="ml-auto font-mono">{view.score.join("–")}</span>{/if}
          </span>
          {#if view.me !== null}
            <p class="mt-1 text-[0.65rem] font-normal opacity-70">
              {t("game.keysHelp")}
            </p>
          {/if}
        </div>

        {#if view.me !== null}
          <div class="flex justify-center" data-testid="my-hand">
            <Hand
              cards={view.my_cards}
              width={92}
              open={myTurn}
              keys={myTurn}
              playable={(c) => !busy && canPlay(view, c.number, c.suit)}
              onPlay={(c) => onAct({ kind: "jugar", card: c, number: null, sena: null })}
              label={t("game.myHand")}
            />
          </div>
          <div class="flex justify-end">
            {#if !busy}<ActionBar actions={view.actions} {onAct} />{/if}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <MoveLog {view} text={(e) => describe(e, false)} />
</div>

{#if helpOpen}<HelpDialog onClose={() => (helpOpen = false)} />{/if}

<style>
  .camera {
    transition: transform 0.4s ease-out;
    transform-style: preserve-3d;
  }

  /* The room and the table. Art from static/ui/ when it exists; gradients underneath. */
  .scene {
    background:
      radial-gradient(ellipse at 50% 35%, rgb(255 214 150 / 0.18), transparent 60%),
      url("/ui/bg-room.webp") center / cover,
      linear-gradient(180deg, #2a1d14, #120c08);
  }
  .felt {
    background:
      radial-gradient(ellipse at 50% 45%, rgb(255 255 255 / 0.12), transparent 65%),
      url("/ui/felt.webp") center / 320px,
      radial-gradient(ellipse at 50% 40%, #2f8a4a, #155d2c 75%);
    border: 14px solid #5b3418;
    border-image: url("/ui/wood.webp") 40 round;
    box-shadow:
      inset 0 0 40px rgb(0 0 0 / 0.55),
      0 0 0 3px #2a160a,
      0 18px 40px rgb(0 0 0 / 0.5);
  }
  .dock {
    background: linear-gradient(0deg, rgb(10 6 3 / 0.85), rgb(10 6 3 / 0.45) 60%, transparent);
  }

  /* The card winning the ronda so far: gold. A tie between teams: both silver. */
  .lead {
    box-shadow:
      0 0 0 3px #fbbf24,
      0 0 22px 6px rgb(251 191 36 / 0.65);
    transform: translateY(-5px) scale(1.06);
    transition:
      transform 0.25s ease-out,
      box-shadow 0.25s ease-out;
  }
  .tie {
    box-shadow:
      0 0 0 3px #e2e8f0,
      0 0 16px 4px rgb(226 232 240 / 0.6);
  }
  .star {
    animation: star-in 0.35s ease-out both;
  }
  @keyframes star-in {
    from {
      scale: 0;
      rotate: -90deg;
    }
  }

  /*
   * A beat: a bot thinks for --think ms (dots), then acts. Everything that shows the move waits
   * for --think. Horizontal centring comes from Tailwind's `translate`, so keyframes only move
   * vertically.
   */
  .thinking {
    animation: think var(--think) linear both;
  }
  .thinking .dot {
    display: inline-block;
    animation: hop 0.9s ease-in-out infinite;
  }
  .thinking .dot:nth-child(2) {
    animation-delay: 0.15s;
  }
  .thinking .dot:nth-child(3) {
    animation-delay: 0.3s;
  }
  @keyframes think {
    0%,
    92% {
      opacity: 1;
    }
    100% {
      opacity: 0;
    }
  }
  @keyframes hop {
    0%,
    100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-4px);
    }
  }

  .fly {
    animation: land 0.6s ease-out var(--think) both;
  }
  .fly-far {
    --from: translate(0, -120px) rotate(-16deg) scale(1.4);
  }
  .fly-near {
    --from: translate(0, 130px) rotate(14deg) scale(1.3);
  }
  .fly-me {
    --from: translate(0, 240px) rotate(8deg) scale(1.8);
  }
  @keyframes land {
    from {
      transform: var(--from);
      opacity: 0;
    }
    30% {
      opacity: 1;
    }
    to {
      transform: none;
      opacity: 1;
    }
  }
  .winner {
    animation: glow 1.6s ease-in-out both;
  }
  @keyframes glow {
    0%,
    100% {
      box-shadow: 0 0 0 0 rgba(250, 204, 21, 0);
    }
    20%,
    80% {
      box-shadow:
        0 0 0 3px #facc15,
        0 0 20px 6px rgba(250, 204, 21, 0.8);
      transform: translateY(-6px) scale(1.12);
    }
  }

  .say {
    animation: say 0.65s ease-out var(--think) both;
  }
  .say.loud {
    animation-name: speak-up;
  }
  @keyframes say {
    0% {
      opacity: 0;
      transform: translateY(8px) scale(0.6);
    }
    25%,
    85% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
    100% {
      opacity: 0;
      transform: translateY(-6px);
    }
  }
  @keyframes speak-up {
    0% {
      opacity: 0;
      transform: translateY(10px) scale(0.4) rotate(-8deg);
    }
    25% {
      opacity: 1;
      transform: scale(1.3) rotate(4deg);
    }
    45% {
      transform: scale(1.1) rotate(-3deg);
    }
    85% {
      opacity: 1;
      transform: scale(1.15);
    }
    100% {
      opacity: 0;
      transform: translateY(-10px) scale(1.2);
    }
  }

  .shout {
    animation: shout 0.65s ease-out var(--think) both;
  }
  @keyframes shout {
    0% {
      opacity: 0;
      transform: scale(0.3);
    }
    30% {
      opacity: 1;
      transform: scale(1.25);
    }
    50%,
    85% {
      opacity: 1;
      transform: scale(1);
    }
    100% {
      opacity: 0;
      transform: scale(1.1);
    }
  }

  .banner {
    animation: banner 1.6s ease-out both;
  }
  @keyframes banner {
    0% {
      opacity: 0;
      transform: translateY(16px) scale(0.85);
    }
    15%,
    85% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
    100% {
      opacity: 0;
      transform: translateY(-8px);
    }
  }

  /* Cards travelling across the table: to the mazo, or dealt from it. */
  .travel {
    left: var(--x0);
    top: var(--y0);
    translate: -50% -50%;
    animation: travel 0.55s ease-in-out calc(var(--think) + var(--i) * 70ms) both;
  }
  .travel.deal {
    animation-duration: 0.45s;
    animation-delay: calc(var(--i) * 110ms);
  }
  @keyframes travel {
    from {
      left: var(--x0);
      top: var(--y0);
      opacity: 0;
      rotate: -20deg;
    }
    20% {
      opacity: 1;
    }
    85% {
      opacity: 1;
    }
    to {
      left: var(--x1);
      top: var(--y1);
      opacity: 0;
      rotate: 0deg;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .camera {
      transition: none;
    }
    .fly,
    .say,
    .say.loud,
    .shout,
    .banner,
    .winner {
      animation-name: fade;
    }
    .travel {
      display: none;
    }
    @keyframes fade {
      0%,
      100% {
        opacity: 0;
      }
      20%,
      80% {
        opacity: 1;
      }
    }
  }
</style>
