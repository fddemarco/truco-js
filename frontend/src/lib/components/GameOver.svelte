<script lang="ts">
  import type { GameView } from "$lib/api/client";
  import { CARD_BACK, cardName, suitSrc, type Suit } from "$lib/cards";
  import { isMessageKey, t } from "$lib/i18n.svelte";

  interface Props {
    view: GameView;
    /** The viewer's team; null for a spectator, who gets no win or loss. */
    myTeam: number | null;
    nameOf: (seat: number) => string;
    /** Back to the table, to look at the last mano. */
    onClose: () => void;
  }

  let { view, myTeam, nameOf, onClose }: Props = $props();

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

  // The fun facts, in words. Unknown keys (a newer server) are left out.
  const facts = $derived(
    view.stats.flatMap((f) => {
      const key = `stat.${f.key}`;
      if (!isMessageKey(key)) return [];
      return [
        t(key, {
          name: f.seat != null ? nameOf(f.seat) : "",
          value: f.value ?? "",
          mano: f.mano ?? "",
          cards: f.cards.map((c) => cardName(c.number, c.suit as Suit)).join(", "),
        }),
      ];
    }),
  );

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
      <button
        type="button"
        class="rounded-xl bg-white/15 px-5 py-2 font-bold hover:bg-white/25"
        onclick={onClose}>{t("end.table")}</button
      >
    </nav>

    {#if facts.length}
      <section>
        <h3 class="mb-1.5 text-sm font-semibold tracking-wide text-amber-200 uppercase">
          {t("end.facts")}
        </h3>
        <ul class="space-y-1 text-sm leading-snug" data-testid="facts">
          {#each facts as fact, i (i)}
            <li class="fact" style="--i: {i}">{fact}</li>
          {/each}
        </ul>
      </section>
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
