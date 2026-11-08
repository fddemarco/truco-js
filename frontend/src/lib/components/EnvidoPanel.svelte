<script lang="ts">
  import type { GameView } from "$lib/api/client";
  import { ACTION_LABELS, envidoBoard } from "$lib/game";
  import { t } from "$lib/i18n.svelte";
  import Avatar from "./Avatar.svelte";

  interface Props {
    view: GameView;
    nameOf: (seat: number | null | undefined) => string;
    /** The envido result is being announced (its beat is on screen). */
    announcing?: boolean;
  }

  let { view, nameOf, announcing = false }: Props = $props();

  // Everyone at the table sees this, players and spectators alike: what the canto is worth,
  // each number said in turn and who holds the best, then who won it.
  const board = $derived(envidoBoard(view, announcing));
  const TEAM_TEXT = ["text-indigo-200", "text-rose-200"];
</script>

{#if board}
  <div
    class="envido-panel pointer-events-none flex min-w-56 flex-col gap-1.5 rounded-xl px-4 py-2.5 text-sm text-white shadow-xl {board.kind ===
    'result'
      ? 'gold text-amber-950'
      : 'bg-slate-950/80 ring-1 ring-amber-200/30'}"
    role="status"
    data-testid="envido-panel"
    data-kind={board.kind}
  >
    <div class="flex items-center justify-between gap-3">
      <span class="font-black tracking-wide uppercase">{board.label}</span>
      {#if board.kind === "stakes" && board.chanter !== null}
        <span class="text-xs opacity-70">{nameOf(board.chanter)}</span>
      {/if}
    </div>

    {#if board.kind === "stakes"}
      <div class="flex items-center gap-3 font-semibold" data-testid="envido-stakes">
        <span class="text-emerald-300">
          {ACTION_LABELS.quiero}
          {#if board.quiero.length === 1}
            +{board.quiero[0]}
          {:else}
            {#each board.quiero as q, team (team)}
              <span class="ml-1 {TEAM_TEXT[team]}" title={view.team_names[team]}
                >{view.team_names[team]} +{q}</span
              >
            {/each}
          {/if}
        </span>
        <span class="text-red-300">{ACTION_LABELS.no_quiero} +{board.noQuiero}</span>
      </div>
    {/if}

    {#if board.said.length}
      <ol class="flex flex-col gap-1" data-testid="envido-said">
        {#each board.said as s (s.seat)}
          <li
            class="flex items-center gap-2 rounded-lg px-1 {s.best
              ? board.kind === 'result'
                ? 'bg-amber-950/15 font-black'
                : 'bg-amber-300/20 font-bold'
              : 'opacity-80'}"
            data-best={s.best || undefined}
          >
            <Avatar character={view.seats[s.seat].character} label={nameOf(s.seat)} class="w-6" />
            <span class="flex-1">{nameOf(s.seat)}</span>
            <span class="font-mono">{s.number ?? ACTION_LABELS.son_buenas}</span>
            {#if s.best}<span aria-hidden="true">★</span>{/if}
          </li>
        {/each}
      </ol>
    {/if}

    {#if board.kind === "declaring" && board.next !== null}
      <span class="text-xs text-amber-200/80"
        >{t("game.envidoNext", { name: nameOf(board.next) })}</span
      >
    {/if}

    {#if board.kind === "result"}
      <div class="pop flex items-center justify-between gap-3 font-black">
        <span>
          {board.winner !== null
            ? t("game.envidoFor", { name: nameOf(board.winner) })
            : t("game.envidoTeam", { team: view.team_names[board.team] })}
        </span>
        <span class="font-mono text-lg">+{board.points}</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .gold {
    background: linear-gradient(135deg, #fde68a, #f59e0b 60%, #d97706);
  }
  .envido-panel {
    animation: rise 0.25s ease-out;
  }
  .pop {
    animation: pop 0.5s cubic-bezier(0.2, 1.6, 0.4, 1);
  }
  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(6px) scale(0.97);
    }
  }
  @keyframes pop {
    0% {
      transform: scale(0.6);
      opacity: 0;
    }
  }
</style>
