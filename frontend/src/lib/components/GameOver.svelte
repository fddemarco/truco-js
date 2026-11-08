<script lang="ts">
  import type { GameView } from "$lib/api/client";
  import { avatarSrc, characterFor } from "$lib/avatar/avatar";
  import { CARD_BACK, cardName, suitSrc, type Suit } from "$lib/cards";
  import { isMessageKey, t } from "$lib/i18n.svelte";
  import PlayingCard from "./PlayingCard.svelte";

  interface Props {
    view: GameView;
    /** The viewer's team; null for a spectator, who gets no win or loss. */
    myTeam: number | null;
    nameOf: (seat: number) => string;
  }

  let { view, myTeam, nameOf }: Props = $props();

  const winner = $derived(view.result?.winner ?? null);
  const outcome = $derived(
    myTeam === null || winner === null ? "neutral" : winner === myTeam ? "win" : "lose",
  );
  const title = $derived(
    outcome === "win"
      ? t("end.win")
      : outcome === "lose"
        ? t("end.lose")
        : winner !== null
          ? t("end.winner", { team: view.team_names[winner] })
          : t("game.noWinner"),
  );

  // The fun facts as medallions: a short title, who, and the number or the cards. The full
  // sentence is a tooltip. Unknown keys (a newer server) are left out.
  const facts = $derived(
    view.stats.flatMap((f) => {
      const key = `stat.${f.key}`;
      const title = `statTitle.${f.key}`;
      if (!isMessageKey(key) || !isMessageKey(title)) return [];
      const seat = f.seat ?? null;
      return [
        {
          key: f.key,
          title: t(title),
          seat,
          value: f.value,
          cards: f.key === "strongest_hand" ? f.cards : [],
          text: t(key, {
            name: seat !== null ? nameOf(seat) : "",
            value: f.value ?? "",
            mano: f.mano ?? "",
            cards: f.cards.map((c) => cardName(c.number, c.suit as Suit)).join(", "),
          }),
        },
      ];
    }),
  );
  const manos = $derived(facts.find((f) => f.key === "manos") ?? null);
  const awards = $derived(facts.filter((f) => f.key !== "manos" && f.seat !== null));

  function character(seat: number) {
    return view.seats?.[seat]?.character ?? characterFor(seat);
  }

  // Win: the four suits rain down in gold. Lose: face-down cards drift down and fade.
  const SUITS: Suit[] = ["espada", "basto", "oro", "copa"];
  const pieces = Array.from({ length: 18 }, (_, i) => ({
    left: (i * 37) % 100,
    delay: (i * 173) % 1400,
    spin: ((i * 53) % 60) - 30,
    suit: SUITS[i % 4],
  }));

  function leave() {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
  }
</script>

<div
  class="end absolute inset-0 z-50 flex items-center justify-center overflow-hidden"
  data-outcome={outcome}
  data-testid="game-over"
  role="dialog"
  aria-modal="true"
  aria-label={title}
>
  <div class="veil absolute inset-0"></div>

  {#if outcome !== "neutral"}
    <div class="pointer-events-none absolute inset-0" aria-hidden="true">
      {#each pieces as p, i (i)}
        <img
          class="piece absolute -top-16 {outcome === 'win' ? 'h-8 w-8' : 'w-10 rounded shadow-lg'}"
          src={outcome === "win" ? suitSrc(p.suit) : CARD_BACK}
          alt=""
          style="left: {p.left}%; --delay: {p.delay}ms; --spin: {p.spin}deg"
        />
      {/each}
    </div>
  {/if}

  <div
    class="panel relative flex max-h-[90%] w-[min(34rem,92%)] flex-col gap-4 overflow-y-auto rounded-3xl p-6 text-amber-50 shadow-2xl"
  >
    <div class="text-center">
      <h2 class="title text-4xl font-black tracking-wide">{title}</h2>
      <p class="mt-1 font-mono text-2xl font-bold" data-testid="final-score">
        <span class="text-indigo-200">{view.team_names[0]} {view.score[0]}</span>
        <span class="text-amber-100/50">–</span>
        <span class="text-rose-200">{view.score[1]} {view.team_names[1]}</span>
      </p>
      {#if manos}
        <p
          class="mt-1 inline-flex items-center gap-1.5 rounded-full bg-black/25 py-0.5 pr-3 pl-0.5 text-sm font-semibold text-amber-100/90"
          title={manos.text}
          data-testid="manos"
        >
          <img src="/ui/stats/manos.svg" alt="" class="h-6 w-6" />
          {t("end.manos", { n: manos.value ?? 0 })}
        </p>
      {/if}
    </div>

    <nav class="flex flex-wrap justify-center gap-2">
      <a
        href="/play"
        class="rounded-xl bg-amber-400 px-5 py-2 font-black text-amber-950 shadow hover:bg-amber-300"
        onclick={leave}>{t("end.newGame")}</a
      >
      <a
        href="/"
        class="rounded-xl bg-white/15 px-5 py-2 font-bold hover:bg-white/25"
        onclick={leave}>{t("end.home")}</a
      >
    </nav>

    {#if awards.length}
      <ul
        class="grid grid-cols-2 gap-2.5 sm:grid-cols-3"
        aria-label={t("end.facts")}
        data-testid="facts"
      >
        {#each awards as f, i (f.key)}
          <!-- focusable so the keyboard reaches the sentence in its tooltip -->
          <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
          <li
            class="fact group relative flex flex-col items-center gap-1 rounded-2xl bg-black/25 px-2 pt-3 pb-2 text-center ring-1 ring-amber-200/15 outline-none hover:bg-black/35 hover:ring-amber-300/50 focus-visible:ring-2 focus-visible:ring-amber-300"
            style="--i: {i}"
            tabindex="0"
            aria-describedby="fact-{f.key}"
            data-testid="fact-{f.key}"
          >
            <div class="relative">
              <img src="/ui/stats/{f.key}.svg" alt="" class="medal h-14 w-14" />
              <img
                src={avatarSrc(character(f.seat!))}
                alt=""
                class="absolute -right-3 -bottom-1 h-8 w-8 rounded-full bg-amber-950 object-cover ring-2 ring-amber-300"
              />
            </div>
            <span class="text-[0.65rem] font-bold tracking-wider text-amber-200/80 uppercase"
              >{f.title}</span
            >
            <span class="max-w-full truncate text-sm font-semibold">{nameOf(f.seat!)}</span>
            {#if f.cards.length}
              <span class="flex gap-0.5" aria-hidden="true">
                {#each f.cards as c (`${c.number}-${c.suit}`)}
                  <PlayingCard number={c.number} suit={c.suit as Suit} class="w-6" />
                {/each}
              </span>
            {:else if f.value != null}
              <span class="font-mono text-2xl leading-none font-black text-amber-300"
                >{f.value}</span
              >
            {/if}
            <span
              id="fact-{f.key}"
              role="tooltip"
              class="tip pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-52 -translate-x-1/2 rounded-lg bg-slate-950/95 px-3 py-2 text-xs leading-snug font-medium text-amber-50 opacity-0 shadow-xl ring-1 ring-amber-200/30 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
              >{f.text}</span
            >
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .veil {
    animation: veil 0.6s ease-out both;
  }
  [data-outcome="win"] .veil {
    background: radial-gradient(circle at 50% 40%, rgb(251 191 36 / 0.35), rgb(10 6 3 / 0.85) 65%);
  }
  [data-outcome="lose"] .veil {
    background: radial-gradient(circle at 50% 40%, rgb(30 41 59 / 0.6), rgb(2 2 6 / 0.92) 70%);
    backdrop-filter: grayscale(0.7);
  }
  [data-outcome="neutral"] .veil {
    background: rgb(10 6 3 / 0.8);
  }
  .panel {
    background: linear-gradient(160deg, rgb(74 44 23 / 0.95), rgb(30 17 8 / 0.95));
    border: 1px solid rgb(234 179 8 / 0.35);
    animation: rise 0.6s cubic-bezier(0.2, 1.3, 0.4, 1) 0.2s both;
  }
  [data-outcome="win"] .title {
    color: #fde68a;
    text-shadow:
      0 0 18px rgb(251 191 36 / 0.8),
      0 2px 0 #92400e;
    animation: glow 1.6s ease-in-out 0.8s infinite alternate;
  }
  [data-outcome="lose"] .title {
    color: #cbd5e1;
    text-shadow: 0 2px 0 #0f172a;
  }
  .piece {
    animation: fall 3.2s ease-in var(--delay) both;
  }
  [data-outcome="win"] .piece {
    filter: drop-shadow(0 0 6px rgb(251 191 36 / 0.9)) sepia(1) saturate(4) hue-rotate(-10deg);
    animation-duration: 2.6s;
    animation-iteration-count: 2;
  }
  [data-outcome="lose"] .piece {
    animation-timing-function: linear;
    animation-duration: 5s;
    opacity: 0.7;
  }
  .fact {
    animation: rise 0.4s ease-out calc(0.8s + var(--i) * 120ms) both;
  }
  .medal {
    filter: drop-shadow(0 3px 6px rgb(0 0 0 / 0.5));
    transition: transform 0.2s ease-out;
  }
  .fact:hover .medal,
  .fact:focus-visible .medal {
    transform: scale(1.08) rotate(-4deg);
  }
  @keyframes veil {
    from {
      opacity: 0;
    }
  }
  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(16px) scale(0.96);
    }
  }
  @keyframes glow {
    to {
      text-shadow:
        0 0 30px rgb(251 191 36 / 1),
        0 2px 0 #92400e;
    }
  }
  @keyframes fall {
    from {
      transform: translateY(0) rotate(0deg);
      opacity: 0;
    }
    10% {
      opacity: 1;
    }
    to {
      transform: translateY(110vh) rotate(var(--spin));
      opacity: 0;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .veil,
    .panel,
    .title,
    .piece,
    .fact {
      animation: none !important;
    }
    .piece {
      display: none;
    }
  }
</style>
