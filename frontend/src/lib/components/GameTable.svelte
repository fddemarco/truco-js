<script lang="ts">
  import { onMount } from "svelte";
  import type { GameAction, GameEvent, GameView } from "$lib/api/client";
  import { BANNERS, ENVIDO_STAGGER_MS, LEAVE, LOUD, SWEEP_MS, type Beat } from "$lib/animation";
  import { play } from "$lib/audio.svelte";
  import type { BodySpot, Sena } from "$lib/avatar/avatar";
  import { cardName, type Suit } from "$lib/cards";
  import {
    ACTION_LABELS,
    HAND_KINDS,
    across,
    activeSenas,
    bestSaid,
    canPlay,
    envidoSaid,
    leadingCards,
    prompt,
    type Prompt,
    tableColumns,
  } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import { actionForKey, commandForCode, senaForCode } from "$lib/keys";
  import { bindings } from "$lib/profile.svelte";
  import ActionBar from "./ActionBar.svelte";
  import Hand from "./Hand.svelte";
  import GameOver from "./GameOver.svelte";
  import GameSettings, { type GameSettingsTab } from "./GameSettings.svelte";
  import KeyMap from "./KeyMap.svelte";
  import Mazo from "./Mazo.svelte";
  import MoveLog from "./MoveLog.svelte";
  import PlayingCard from "./PlayingCard.svelte";
  import Scoreboard from "./Scoreboard.svelte";
  import SeatBadge from "./SeatBadge.svelte";

  interface Props {
    view: GameView;
    /** The seat whose eyes the camera uses: the viewer's, or seat 0 for spectators. */
    viewer: number;
    /** server clock − local clock, to time señas. */
    offset?: number;
    /** The move being animated, if any. */
    beat?: Beat | null;
    /** The beat's player is still thinking: its move isn't on the table yet. */
    thinking?: boolean;
    /** On a new deal, the seats that had cards on the table: they go back to the mazo first. */
    swept?: number[];
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
    thinking = false,
    swept = [],
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

  // --- full screen ---------------------------------------------------------------------------
  // The table fills the window by default (and the screen, when the browser lets it: the
  // new-game button asks for it). F11 and the corner button toggle it, Escape steps out. F11
  // goes through the Fullscreen API like the button, so the page always knows the state and
  // Escape, F11 and the button agree. Every change says, for a moment, how to undo it.
  let immersive = $state(true);
  let screenWide = false; // the browser itself is in full screen
  let fsHint = $state<"enter" | "exit" | "back" | null>(null);
  let fsHintTimer: ReturnType<typeof setTimeout> | undefined;
  function hintFullscreen(kind: "enter" | "exit" | "back") {
    fsHint = kind;
    clearTimeout(fsHintTimer);
    fsHintTimer = setTimeout(() => (fsHint = null), 3500);
  }
  function setImmersive(on: boolean) {
    immersive = on;
    if (on && !document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    }
    if (!on && document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    hintFullscreen(on ? "exit" : "back");
  }
  function fullscreenChange() {
    // The browser's own Escape leaves full screen without a keydown reaching the page.
    if (screenWide && !document.fullscreenElement) {
      immersive = false;
      hintFullscreen("back");
    }
    screenWide = !!document.fullscreenElement;
  }
  onMount(() => {
    // Arriving by a link (no click to allow it), the browser keeps its bars: say how to go
    // full screen.
    const id = setTimeout(() => !document.fullscreenElement && hintFullscreen("enter"), 800);
    return () => {
      clearTimeout(id);
      clearTimeout(fsHintTimer);
    };
  });

  // The end of the partido: once the last move has played out.
  const gameOver = $derived(!!view.result && !busy);

  // The moves: shown while the pointer is over their button or the panel, never by a click.
  let logOpen = $state(false);

  // A chime when the move passes to the viewer (once the table has caught up).
  const myMove = $derived(
    !busy && view.me !== null && view.to_act === view.me && view.actions.length > 0,
  );
  let hadMove = false;
  $effect(() => {
    if (myMove && !hadMove) play("turn");
    hadMove = myMove;
  });

  // --- seating and camera -----------------------------------------------------------------
  // Columns are physical positions along the table, from the viewer's left to right: the
  // player across in the top row, the one on the viewer's side in the bottom row. One against
  // one, both sit in the middle column and the others are empty (null).
  const players = $derived(view.seats.length);
  const columns = $derived(tableColumns(viewer, players));
  const far = $derived(columns.far);
  const near = $derived(columns.near);
  const myTeam = $derived(view.me !== null ? view.seats[view.me].team : null);

  let focus = $state(0);
  let focusedFor = -1;
  $effect(() => {
    // A new viewer (hot-seat) looks straight across first.
    if (viewer !== focusedFor) {
      focusedFor = viewer;
      look(across(viewer, players));
    }
  });
  const focusIndex = $derived(Math.max(0, far.indexOf(focus)));

  function look(seat: number) {
    focus = seat;
    onLook?.(seat);
  }
  function pan(step: number) {
    const i = Math.min(2, Math.max(0, focusIndex + step));
    const seat = far[i];
    if (seat != null && seat !== focus) look(seat);
  }
  /** Someone to turn to on that side. */
  const canPan = (step: number) => far[focusIndex + step] != null;

  /** Where a seat sits in the scene, in % of its width and height (for flying cards). */
  function anchor(seat: number): { x: number; y: number } {
    const top = far.indexOf(seat);
    const col = top >= 0 ? top : near.indexOf(seat);
    return { x: ((col + 0.5) * 100) / 3, y: top >= 0 ? 10 : 70 };
  }
  /** The mazo sits on the felt in front of the dealer, beside their stack. */
  const mazo = $derived.by(() => {
    const a = anchor(view.dealer);
    return { x: a.x + 11, y: a.y < 50 ? 31 : 53 };
  });

  // Señas are only seen face to face: the player across in focus (14.4). Spectators see all.
  // The viewer's own face shows the seña while its key is held, not the server's copy, which
  // only arrives on release and would replay it.
  const senas = $derived(activeSenas(view.senas, now + offset));
  function senaOf(seat: number) {
    if (view.me !== null && seat === view.me) return making ?? undefined;
    if (view.me !== null && seat !== focus) return undefined;
    return senas.get(seat);
  }

  /** Mano, or a pie: each team has its own, its last player in the order. */
  function roleOf(seat: number): "mano" | "pie" | null {
    if (view.mano === seat) return "mano";
    if (view.pies.includes(seat)) return "pie";
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
      case "reparto": {
        // A beat keeps its event: the deal's modality is there.
        const hk = ("event" in e ? e.event : e).hand_kind;
        const kind = hk ? ` · ${HAND_KINDS[hk] ?? hk}` : "";
        return `— ${t("game.handNumber", { n: e.number ?? "" })}${kind} —`;
      }
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
        // No quiero has no winner seat: the chanter's team takes the points.
        const pts = e.points ?? [0, 0];
        const team = pts[1] > pts[0] ? 1 : 0;
        if (e.seat == null)
          return `${t("game.envidoTeam", { team: view.team_names[team] })} (+${pts[team]})`;
        const won = t(e.seat === view.me ? "game.envidoWonMe" : "game.envidoWon");
        const tanto = e.number != null ? ` ${t("game.withTanto", { n: e.number })}` : "";
        return `${who} ${won}${tanto} (+${pts[team]})`;
      }
      case "interferencia":
        return by(t("game.interference"));
      case "jugar":
        return e.card ? by(cardName(e.card.number, e.card.suit as Suit)) : who;
      case "declarar":
        return by(t("game.tantoSaid", { n: e.number ?? "" }));
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

  // The current beat, split into what each part of the table draws. While its player thinks,
  // only the thinking dots show; the move is drawn once it's made.
  const move = $derived(thinking ? null : beat);
  // Numbers said in the envido stay up in their own bubbles (below), not as passing words.
  const speaking = $derived(
    move &&
      move.seat !== null &&
      !["jugar", "declarar", "son_buenas"].includes(move.kind) &&
      !BANNERS.has(move.kind)
      ? move
      : null,
  );
  // Only a new deal and the end of the match get a banner. Rondas, envidos and the end of a
  // mano show on the cards, the scoreboard and the log instead.
  const banner = $derived(
    move && (move.kind === "reparto" || move.kind === "resultado") ? move : null,
  );
  const leaving = $derived(move && move.seat !== null && LEAVE.has(move.kind) ? move : null);
  const dealing = $derived(move?.kind === "reparto" ? move : null);

  // --- the envido, said out loud ---------------------------------------------------------------
  // Each number (or "son buenas") comes up over its player, ENVIDO_STAGGER_MS after the one
  // before, and stays until the envido is over. The best so far turns gold.
  const envido = $derived(envidoSaid(view, move?.kind ?? null));
  let revealed = $state<number[]>([]);
  let lastReveal = 0;
  $effect(() => {
    const said = envido;
    if (!said.length) {
      if (revealed.length) revealed = [];
      lastReveal = 0;
      return;
    }
    const next = said.find((s) => !revealed.includes(s.seat));
    if (!next) return;
    const id = setTimeout(
      () => {
        lastReveal = Date.now();
        revealed = [...revealed, next.seat];
      },
      Math.max(0, lastReveal + ENVIDO_STAGGER_MS - Date.now()),
    );
    return () => clearTimeout(id);
  });
  const envidoShown = $derived(envido.filter((s) => revealed.includes(s.seat)));
  const envidoBest = $derived(bestSaid(envidoShown, view));

  function flying(seat: number) {
    return move?.kind === "jugar" && move.seat === seat ? move.id : null;
  }
  function wonRonda(seat: number) {
    return move?.kind === "ronda" && move.seat === seat;
  }
  function acting(seat: number) {
    return beat !== null && beat.seat === seat && !BANNERS.has(beat.kind);
  }

  // --- input ---------------------------------------------------------------------------------
  // Timed señas: interactive mode, with a partner to signal (not one against one).
  const timedSenas = $derived(view.mode === "interactive" && view.seats.length > 2);
  // Interactive señas: hold a key, release to send with the held time as duration.
  const held = new Map<string, number>();
  // The seña whose key is down, shown on the viewer's own face until it is released.
  let making = $state<{ code: string; sena: Sena; spot: BodySpot } | null>(null);
  function release() {
    held.clear();
    making = null;
    keymapOpen = false;
  }
  const keys = $derived(bindings());
  let settingsTab = $state<GameSettingsTab | null>(null);
  // Tab, held: the keys in use, over the table.
  let keymapOpen = $state(false);
  function typing(target: EventTarget | null) {
    return (
      target instanceof HTMLElement && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)
    );
  }
  function keydown(e: KeyboardEvent) {
    if (typing(e.target) || e.ctrlKey || e.metaKey || e.altKey || settingsTab) return;
    if (e.code === "F11") {
      e.preventDefault();
      setImmersive(!immersive);
      return;
    }
    if (e.code === "Tab") {
      e.preventDefault();
      keymapOpen = true;
      return;
    }
    if (e.code === "Escape" && immersive) {
      setImmersive(false);
      return;
    }
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
    if (!onSena || !timedSenas || e.repeat) return;
    const sena = senaForCode(e.code, keys);
    if (sena) {
      e.preventDefault();
      held.set(e.code, Date.now());
      making = { code: e.code, ...sena };
    }
  }
  function keyup(e: KeyboardEvent) {
    if (e.code === "Tab") keymapOpen = false;
    const start = held.get(e.code);
    held.delete(e.code);
    if (making?.code === e.code) making = null;
    const sena = senaForCode(e.code, keys);
    if (start === undefined || !sena || !onSena) return;
    onSena(sena.sena, sena.spot, Math.min(5000, Math.max(150, Date.now() - start)));
  }

  const TONES = {
    go: "border-emerald-400 bg-emerald-50/95 text-emerald-900",
    answer: "border-amber-400 bg-amber-50/95 text-amber-950",
    wait: "border-slate-300 bg-white/90 text-slate-700",
    done: "border-indigo-400 bg-indigo-50/95 text-indigo-950",
  };
</script>

<svelte:window onkeydown={keydown} onkeyup={keyup} onblur={release} />
<svelte:document onfullscreenchange={fullscreenChange} />

{#snippet stack(seat: number, from: "far" | "near" | "me")}
  {@const cards = view.seats[seat].played}
  {@const fly = flying(seat)}
  {@const won = wonRonda(seat)}
  {@const lead = leads(seat)}
  <!-- Played cards pile up; hovering spreads them out to read every one. -->
  <div
    class="stack relative h-24"
    style="width: {56 + 12 * Math.max(0, cards.length - 1)}px; --n: {Math.max(0, cards.length - 1)}"
    data-testid="stack-{seat}"
  >
    {#each cards as c, i (`${c.number}-${c.suit}`)}
      {@const last = i === cards.length - 1}
      <div
        class="played absolute rounded-[4%/2.7%] {fly !== null && last
          ? `fly fly-${from}`
          : ''} {won && last ? 'winner' : ''} {lead && last ? lead : ''}"
        style="--i: {i}; z-index: {i}"
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
  {@const tanto = envidoShown.find((s) => s.seat === seat)}
  {#if tanto}
    {@const best = envidoBest === seat}
    <div
      class="tanto pointer-events-none absolute left-1/2 z-30 -translate-x-1/2 rounded-full px-3 py-1 font-extrabold whitespace-nowrap shadow-lg {best
        ? 'best text-lg text-amber-950'
        : tanto.number === null
          ? 'bg-white/90 text-sm text-slate-600'
          : 'bg-white text-lg text-slate-900'} {where}"
      role="status"
      data-testid="envido-said-{seat}"
      data-best={best || undefined}
    >
      {tanto.number ?? ACTION_LABELS.son_buenas}
      {#if best}
        <span
          class="star absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-amber-400 text-[0.7rem] text-amber-950 shadow"
          aria-hidden="true">★</span
        >
      {/if}
    </div>
  {/if}
  {#if thinking && beat && beat.seat === seat}
    {#key beat.id}
      <div
        class="thinking pointer-events-none absolute left-1/2 z-30 -translate-x-1/2 rounded-full bg-white/95 px-3 py-1 text-sm font-bold text-slate-600 shadow {where}"
        style="--think: {beat.think}ms"
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
        role="status"
      >
        {said(speaking)}
      </div>
    {/key}
  {/if}
{/snippet}

{#snippet glyph(path: string)}
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
    {@html path}
  </svg>
{/snippet}

<!-- First person at a 3-3 table, filling the window unless the player stepped out of it. -->
<div
  class="scene overflow-hidden [perspective:1100px] {immersive
    ? 'fixed inset-0 z-50'
    : 'relative h-[calc(100vh-6rem)] min-h-[40rem] rounded-2xl shadow-2xl'}"
  data-testid="scene"
  data-immersive={immersive}
>
  <!-- the match: a see-through plaque on the left, out of the table's way -->
  <div class="absolute top-1/2 left-3 z-30 -translate-y-1/2">
    <Scoreboard {view} {myTeam} {nameOf} />
  </div>

  <!-- the table, right of the scoreboard -->
  <div class="stage absolute inset-y-0 right-0 left-64">
    <!-- The camera pans to the player across in focus. -->
    <div
      class="camera absolute inset-0"
      style="transform: translateX({(1 - focusIndex) * 8}%) rotateY({(focusIndex - 1) * -6}deg)"
      data-focus={focus}
    >
      <div class="felt absolute inset-x-[2%] top-[21%] bottom-[37%] rounded-[3rem]"></div>

      <!-- the mazo, in front of the dealer -->
      <div
        class="absolute z-10 -translate-x-1/2 -translate-y-1/2"
        style="left: {mazo.x}%; top: {mazo.y}%"
        data-testid="mazo"
      >
        <Mazo class="w-11" state={cutting ? "cutting" : nextDeal && !busy ? "shuffling" : "idle"} />
        <span class="absolute -bottom-4 left-1/2 -translate-x-1/2 text-[0.6rem] text-white/80"
          >{t("game.mazo")}</span
        >
      </div>

      <!-- the players across, at the far edge -->
      <div class="absolute inset-x-0 top-0 grid h-[21%] grid-cols-3">
        {#each far as top, col (col)}
          {#if top === null}<div></div>{:else}
            {@const ts = view.seats[top]}
            <div class="flex justify-center pt-2">
              <div class="relative flex flex-col items-center gap-1" data-testid="seat-{top}">
                {@render bubble(top, "over")}
                <SeatBadge
                  seat={ts}
                  label={nameOf(top)}
                  look={top === focus ? "focus" : "dim"}
                  size={top === focus ? "lg" : "md"}
                  mine={ts.team === myTeam}
                  role={roleOf(top)}
                  ownPie={view.seats[top].team === (myTeam ?? 0)}
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
                    {#each ts.shown as c (`${c.number}-${c.suit}`)}
                      <PlayingCard number={c.number} suit={c.suit as Suit} class="w-8" />
                    {/each}
                  </div>
                {/if}
              </div>
            </div>
          {/if}
        {/each}
      </div>

      <!-- the played cards on the felt, each stack in front of its player -->
      <div class="absolute inset-x-0 top-[23%] bottom-[39%] grid grid-cols-3">
        {#each [0, 1, 2] as col (col)}
          {@const top = far[col]}
          {@const bottom = near[col]}
          <div class="flex flex-col items-center justify-between py-2">
            {#if top !== null}{@render stack(top, "far")}{/if}
            {#if bottom !== null}{@render stack(bottom, bottom === viewer ? "me" : "near")}{/if}
          </div>
        {/each}
      </div>

      <!-- the viewer's side, at the near edge: a mirror of the far one -->
      <div class="absolute inset-x-0 top-[63%] grid h-[17%] grid-cols-3">
        {#each near as bottom, col (col)}
          {#if bottom === null}<div></div>{:else}
            {@const bs = view.seats[bottom]}
            <div class="flex justify-center">
              <div
                class="relative flex flex-col items-center justify-start gap-1"
                data-testid="seat-{bottom}"
              >
                {@render bubble(bottom, "above")}
                {#if bottom !== viewer}
                  <Hand
                    cards={bs.cards_left}
                    width={26}
                    label={t("game.handOf", { name: bs.name })}
                  />
                {/if}
                <SeatBadge
                  seat={bs}
                  label={nameOf(bottom)}
                  look={bottom === viewer && view.me !== null ? "focus" : "dim"}
                  size="md"
                  mine={bs.team === myTeam}
                  role={roleOf(bottom)}
                  ownPie={view.seats[bottom].team === (myTeam ?? 0)}
                  turn={view.to_act === bottom && !busy}
                  acting={acting(bottom)}
                  sena={senaOf(bottom)}
                />
              </div>
            </div>
          {/if}
        {/each}
      </div>

      <!-- a player going to the mazo: their cards slide onto it -->
      {#if leaving && leaving.seat !== null}
        {@const from = anchor(leaving.seat)}
        {#key leaving.id}
          {#each [0, 1, 2] as i (i)}
            <div
              class="travel pointer-events-none absolute z-20"
              style="--x0: {from.x}%; --y0: {from.y}%; --x1: {mazo.x}%; --y1: {mazo.y}%; --i: {i}"
              data-testid="to-mazo"
            >
              <PlayingCard faceDown class="w-9" />
            </div>
          {/each}
        {/key}
      {/if}

      <!-- a new deal: the last mano's cards go back to the mazo, then out to every player -->
      {#if dealing}
        {#key dealing.id}
          {#each swept as seat, i (seat)}
            {@const from = anchor(seat)}
            <div
              class="travel pointer-events-none absolute z-20"
              style="--x0: {from.x}%; --y0: {from.y}%; --x1: {mazo.x}%; --y1: {mazo.y}%; --i: {i}"
              data-testid="sweep"
            >
              <PlayingCard faceDown class="w-9" />
            </div>
          {/each}
          {#each [...far, ...near].filter((s) => s !== null) as seat, i (seat)}
            {@const to = anchor(seat)}
            <div
              class="travel deal pointer-events-none absolute z-20"
              style="--x0: {mazo.x}%; --y0: {mazo.y}%; --x1: {to.x}%; --y1: {to.y}%; --i: {i}; --after: {swept.length
                ? SWEEP_MS
                : 0}ms"
            >
              <PlayingCard faceDown class="w-8" />
            </div>
          {/each}
        {/key}
      {/if}
    </div>

    <button
      class="absolute top-[9%] left-2 z-20 rounded-full bg-white/80 px-3 py-1 text-xl shadow disabled:opacity-30"
      aria-label={t("game.lookLeft")}
      disabled={!canPan(-1)}
      onclick={() => pan(-1)}>‹</button
    >
    <button
      class="absolute top-[9%] right-2 z-20 rounded-full bg-white/80 px-3 py-1 text-xl shadow disabled:opacity-30"
      aria-label={t("game.lookRight")}
      disabled={!canPan(1)}
      onclick={() => pan(1)}>›</button
    >

    {#if banner}
      {#key banner.id}
        <div
          class="banner pointer-events-none absolute top-[40%] left-1/2 z-30 -translate-x-1/2 rounded-xl bg-slate-900/85 px-5 py-2 text-lg font-bold whitespace-nowrap text-white shadow-xl"
          role="status"
        >
          {describe(banner)}
        </div>
      {/key}
    {/if}

    <!-- between manos: the dealer shuffles, the player to their left cuts -->
    {#if nextDeal && !busy}
      <div
        class="absolute top-[42%] left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-full bg-slate-950/80 px-4 py-2 text-sm text-white shadow-xl"
        data-testid="next-deal"
      >
        {#if nextDeal.mine}
          <span>{t("game.cutPrompt")}</span>
          <button
            class="rounded-full bg-amber-400 px-4 py-1 font-bold text-amber-950 hover:bg-amber-300 disabled:opacity-50"
            disabled={cutting}
            onclick={() => onCut?.()}>{t("game.cut")}</button
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
      class="dock absolute inset-x-0 bottom-0 z-20 grid h-[20%] grid-cols-[1fr_auto_1fr] items-end gap-3 px-4 pb-3"
    >
      <div></div>

      {#if view.me !== null}
        <div class="flex justify-center" data-testid="my-hand">
          <Hand
            cards={view.my_cards}
            width={88}
            open
            playable={(c) => !busy && canPlay(view, c.number, c.suit)}
            onPlay={(c) => onAct({ kind: "jugar", card: c, number: null, sena: null })}
            label={t("game.myHand")}
          />
        </div>
        <div class="flex justify-end">
          {#if !busy}<ActionBar actions={view.actions} {onAct} tanto={view.my_tanto} />{/if}
        </div>
      {/if}
    </div>
  </div>

  <!-- top left: full screen, always in sight -->
  <div class="absolute top-3 left-3 z-40">
    <button
      class="rounded-full bg-white/85 p-2 text-slate-700 shadow hover:bg-white"
      aria-label={t(immersive ? "game.exitFullscreen" : "game.fullscreen")}
      aria-keyshortcuts="F11"
      title="{t(immersive ? 'game.exitFullscreen' : 'game.fullscreen')} (F11)"
      onclick={() => setImmersive(!immersive)}
    >
      {@render glyph(
        immersive
          ? '<path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>'
          : '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>',
      )}
    </button>
  </div>

  <!-- upper left, above the scoreboard: Tab shows the keys -->
  <div class="pointer-events-none absolute top-[18%] left-3 z-40">
    <span
      class="hidden w-fit rounded-full bg-slate-950/45 px-2.5 py-1.5 text-[0.65rem] font-semibold text-white/75 backdrop-blur sm:block"
      aria-hidden="true"><kbd class="font-mono">Tab</kbd> · {t("keymap.title")}</span
    >
  </div>

  <!-- bottom left, under the scoreboard: whose move it is -->
  <div class="absolute bottom-3 left-3 z-30 max-w-60">
    <!-- "your turn" needs no words: the playable cards light up green -->
    {#if hint.tone !== "go"}
      <div
        class="rounded-xl border-l-4 px-3 py-2 text-sm font-semibold shadow-lg backdrop-blur {TONES[
          hint.tone
        ]}"
        role="status"
        data-testid="prompt"
        data-tone={hint.tone}
      >
        <span class="flex items-center gap-2">
          {#if hint.tone === "answer"}
            <span class="relative flex h-3 w-3 shrink-0">
              <span
                class="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"
              ></span>
              <span class="relative inline-flex h-3 w-3 rounded-full bg-amber-500"></span>
            </span>
          {/if}
          <span>{t(hint.key, hint.vars ?? {})}</span>
          {#if view.result}<span class="ml-auto font-mono">{view.score.join("–")}</span>{/if}
        </span>
      </div>
    {/if}
  </div>

  <!-- top right: the moves and the menu, both opening on hover only (no click to open or
       close): the panel stays while the pointer is over the button or the panel -->
  <div class="absolute top-3 right-3 z-40 flex items-start gap-2">
    <div
      class="flex flex-col items-end gap-2"
      data-testid="moves"
      role="group"
      aria-label={t("game.moves")}
      onmouseenter={() => (logOpen = true)}
      onmouseleave={() => (logOpen = false)}
    >
      <span
        class="flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-semibold text-slate-700 shadow {logOpen
          ? 'bg-white'
          : 'bg-white/85'}"
      >
        {@render glyph('<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>')}{t(
          "game.moves",
        )}
      </span>
      {#if logOpen}
        <div class="h-[60vh] w-72">
          <MoveLog {view} text={(e) => describe(e, false)} />
        </div>
      {/if}
    </div>
    <div class="group flex flex-col items-end gap-2">
      <span
        class="rounded-full bg-white/85 p-2 text-slate-700 shadow group-hover:bg-white"
        role="img"
        aria-label={t("game.menu")}
      >
        {@render glyph('<path d="M4 6h16M4 12h16M4 18h16"/>')}
      </span>
      <!-- one see-through panel, its items rows of the same table -->
      <div
        class="hidden min-w-52 flex-col divide-y divide-white/15 overflow-hidden rounded-xl bg-slate-900/55 text-white shadow-lg ring-1 ring-white/20 backdrop-blur-md group-hover:flex"
      >
        {#each [{ label: t("settings.howto"), icon: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>', run: () => (settingsTab = "howto") }, { label: t("nav.settings"), icon: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>', run: () => (settingsTab = "sound") }] as item (item.label)}
          <button
            class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm font-semibold transition-colors hover:bg-white/15"
            onclick={item.run}
          >
            {item.label}
            {@render glyph(item.icon)}
          </button>
        {/each}
        <!-- the game goes on without this device; the link brings it back -->
        <a
          href="/"
          class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm font-semibold text-rose-200 hover:bg-white/15"
          onclick={() => document.fullscreenElement && document.exitFullscreen?.().catch(() => {})}
        >
          {t("game.leave")}
          {@render glyph(
            '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
          )}
        </a>
      </div>
    </div>
  </div>

  <!-- how to undo the last full-screen change, for a moment -->
  {#if fsHint}
    <div
      class="theme-table table-glass pointer-events-none absolute bottom-[23%] left-1/2 z-40 -translate-x-1/2 rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap"
      role="status"
      data-testid="fullscreen-hint"
    >
      {@html t(`game.fsHint.${fsHint}`, {
        f11: '<kbd class="rounded border border-amber-200/40 bg-black/30 px-1.5 font-mono text-amber-200">F11</kbd>',
        esc: '<kbd class="rounded border border-amber-200/40 bg-black/30 px-1.5 font-mono text-amber-200">Esc</kbd>',
      })}
    </div>
  {/if}
  {#if gameOver}
    <GameOver {view} {myTeam} nameOf={(seat) => nameOf(seat)} />
  {/if}
</div>

{#if settingsTab}
  <GameSettings tab={settingsTab} onClose={() => (settingsTab = null)} />
{/if}
{#if keymapOpen && !settingsTab}<KeyMap senas={timedSenas} />{/if}

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

  /* A stack spreads out on hover, straight and side by side around its centre, so every card
     played can be read. The stack itself never moves: moving it out from under the pointer
     made the hover flicker on and off. */
  .stack:hover {
    z-index: 30;
  }
  .played {
    left: calc(var(--i) * 12px);
    top: calc(var(--i) * 6px);
    transition:
      left 0.2s ease-out,
      top 0.2s ease-out,
      transform 0.2s ease-out;
  }
  .stack:hover .played {
    /* the stack is 56 + 12n wide: centre the n + 1 cards, 60px apart, on its middle */
    left: calc(var(--n) * 6px + (var(--i) - var(--n) / 2) * 60px);
    top: 0;
    transform: none;
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
  /* A number said in the envido: it pops up, and the best so far turns gold like the card
     winning a ronda (.lead). */
  .tanto {
    animation: tanto-in 0.3s ease-out both;
    transition:
      transform 0.25s ease-out,
      box-shadow 0.25s ease-out,
      background 0.25s ease-out;
  }
  .tanto.best {
    background: linear-gradient(135deg, #fde68a, #fbbf24 55%, #f59e0b);
    box-shadow:
      0 0 0 3px #fbbf24,
      0 0 22px 6px rgb(251 191 36 / 0.65);
    transform: translateY(-5px) scale(1.06);
  }
  @keyframes tanto-in {
    from {
      opacity: 0;
      scale: 0.6;
    }
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
   * A beat: a bot thinks for --think ms (dots), then acts; the move is drawn once it's made.
   * Horizontal centring comes from Tailwind's `translate`, so keyframes only move
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
    animation: land 0.6s ease-out both;
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
    animation: say 0.65s ease-out both;
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
    animation: travel 0.55s ease-in-out calc(var(--i) * 70ms) both;
  }
  .travel.deal {
    animation-duration: 0.45s;
    animation-delay: calc(var(--after, 0ms) + var(--i) * 110ms);
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
    .camera,
    .played,
    .tanto {
      transition: none;
    }
    .tanto {
      animation: none;
    }
    .fly,
    .say,
    .say.loud,
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
