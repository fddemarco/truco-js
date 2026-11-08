/**
 * One game as this browser sees it: the seat tokens it holds, the latest view from the server,
 * the table on screen (which plays the server's steps as beats, see $lib/animation), and the
 * transport that keeps it fresh.
 *
 * Updates: the view is polled every second (the server is stateless serverless functions, so
 * there's no stream to push changes; a poll also keeps this seat online and lets the table
 * deal once its wait is over). Hidden tabs don't poll. Tokens go in the X-Seat-Token header,
 * never in URLs.
 */
import { BeatQueue, isNewer, stepBeats, type Beat } from "$lib/animation";
import { api, errorMessage, type GameAction, type GameView } from "$lib/api/client";
import type { BodySpot, Character, Sena } from "$lib/avatar/avatar";
import { play, sfxFor } from "$lib/audio.svelte";
import { forgetToken, loadHost, loadTokens, nextDeal, saveToken, touchGame } from "$lib/game";
import { t } from "$lib/i18n.svelte";
import { log } from "$lib/log";

export const POLL_MS = 1000;
const CUT_MS = 700; // the cut's animation before the deal is asked for

const seatHeader = (token: string) => ({ "X-Seat-Token": token });

type ApiResult<T> = { data?: T; error?: unknown; response: Response };

/** Take an open seat for this browser; the token is saved. Throws if the server is unreachable. */
export async function joinSeat(
  gameId: string,
  seat: number,
  name: string,
  character: Character | null = null,
): Promise<{ token: string } | { error: string; status: number }> {
  const res = await api.POST("/api/games/{game_id}/join", {
    params: { path: { game_id: gameId } },
    body: { seat, name, character },
  });
  if (!res.data) return { error: errorMessage(res.error), status: res.response.status };
  saveToken(gameId, seat, res.data.token);
  log.info("game.joined", { game_id: gameId, seat });
  return { token: res.data.token };
}

export class TableSession {
  readonly gameId: string;
  tokens = $state<Record<number, string>>({});
  host = $state<string | null>(null);
  seat = $state<number | null>(null); // the seat this device is acting as
  revealed = $state(true);
  // `latest` is what the server sent; `view` is the table on screen. The server sends each
  // move as a step with the table right after it; they play as beats (1-2 s for a bot) and
  // the table shows each step's own view, then catches up with `latest`.
  latest = $state.raw<GameView | null>(null);
  view = $state.raw<GameView | null>(null);
  beat = $state<Beat | null>(null);
  thinking = $state(false); // the beat's player is still thinking: its move isn't made yet
  swept = $state<number[]>([]); // on a deal, the seats whose cards go back to the mazo
  look = $state<number | null>(null); // the player across the camera is on
  offset = $state(0); // server clock minus this device's
  error = $state<string | null>(null);
  offline = $state(false); // the server can't be reached; cleared by the next answer
  cutting = $state(false);

  mySeats = $derived(
    Object.keys(this.tokens)
      .map(Number)
      .sort((a, b) => a - b),
  );
  local = $derived(this.mySeats.length > 1);
  token = $derived(this.seat !== null ? this.tokens[this.seat] : undefined);
  busy = $derived(this.beat !== null);
  // While beats play nothing can be done, and señas stay live.
  display = $derived(
    this.view && this.busy && this.latest
      ? { ...this.view, senas: this.latest.senas, actions: [] }
      : this.view,
  );
  openSeats = $derived(this.view?.seats.filter((s) => s.kind === "human" && !s.joined) ?? []);
  plan = $derived(this.view && !this.busy ? nextDeal(this.view, this.mySeats, this.offset) : null);

  private lastStep = -1; // the newest step queued or shown
  private queue: BeatQueue;
  private gone = false;
  private onGone: () => void;

  constructor(gameId: string, onGone: () => void) {
    this.gameId = gameId;
    this.onGone = onGone;
    this.tokens = loadTokens(gameId);
    this.host = loadHost(gameId);
    this.queue = new BeatQueue(
      (b) => {
        log.debug("beat.start", {
          game_id: gameId,
          beat: b.id,
          kind: b.kind,
          seat: b.seat,
          ms: b.ms,
          think: b.think,
        });
        this.beat = b;
        this.thinking = b.think > 0;
        // While a bot thinks the table stays as it was; then the move is made.
        if (this.thinking) setTimeout(() => this.beat?.id === b.id && this.land(b), b.think);
        else this.land(b);
      },
      () => {
        log.debug("beat.idle", { game_id: gameId, version: this.latest?.version });
        this.beat = null;
        this.thinking = false;
        if (this.latest) this.settle(this.latest);
      },
    );
  }

  /** Connect: fetch the table, then poll. Returns the disconnect. */
  start(): () => void {
    touchGame(this.gameId);
    this.seat = this.mySeats[0] ?? null;
    void this.refresh();
    let timer: ReturnType<typeof setTimeout>;
    const loop = () => {
      timer = setTimeout(() => {
        if (!document.hidden) void this.refresh();
        loop();
      }, POLL_MS);
    };
    loop();
    const visible = () => {
      if (!document.hidden) void this.refresh();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", visible);
      this.queue.stop();
    };
  }

  /** The steps we have: none yet means arriving (the server picks what to replay). */
  private since(): number | null {
    return this.latest ? this.lastStep : null;
  }

  async refresh(): Promise<void> {
    const token = this.token;
    await this.send(
      api.GET("/api/games/{game_id}", {
        params: {
          path: { game_id: this.gameId },
          query: { look: this.look, since: this.since() },
          header: token ? seatHeader(token) : {},
        },
      }),
    );
  }

  async act(action: GameAction): Promise<void> {
    const token = this.token;
    if (!token) return;
    log.info("game.act", {
      game_id: this.gameId,
      seat: this.seat,
      kind: action.kind,
      card: action.card ? `${action.card.number}-${action.card.suit}` : null,
      number: action.number,
    });
    await this.send(
      api.POST("/api/games/{game_id}/act", {
        params: { path: { game_id: this.gameId }, header: seatHeader(token) },
        body: { action, look: this.look, since: this.since() },
      }),
    );
  }

  /** The cutter, on this device, cuts before the table's wait is over. */
  cut(): void {
    const plan = this.plan;
    if (this.cutting || !plan?.mine) return;
    const token = this.tokens[plan.cutter];
    this.cutting = true;
    log.info("game.cut", { game_id: this.gameId, seat: plan.cutter });
    setTimeout(async () => {
      this.cutting = false;
      // The table may have dealt meanwhile (its wait ran out): the next view shows the mano.
      await this.send(
        api.POST("/api/games/{game_id}/deal", {
          params: { path: { game_id: this.gameId }, header: seatHeader(token) },
          body: { look: this.look, since: this.since() },
        }),
        [400, 403],
      );
    }, CUT_MS);
  }

  async sena(s: Sena, spot: BodySpot, durationMs: number): Promise<void> {
    const token = this.token;
    if (!token) return;
    await this.send(
      api.POST("/api/games/{game_id}/sena", {
        params: { path: { game_id: this.gameId }, header: seatHeader(token) },
        body: {
          sena: s,
          spot,
          duration_ms: durationMs,
          target: null,
          look: this.look,
          since: this.since(),
        },
      }),
    );
  }

  async join(seat: number, name: string, character: Character | null): Promise<void> {
    const res = await this.reach(joinSeat(this.gameId, seat, name, character));
    if (!res) return;
    if ("error" in res) {
      this.fail(res.error, res.status);
      return;
    }
    this.tokens = loadTokens(this.gameId);
    this.seat = seat;
    await this.refresh();
  }

  /** The host frees a seat whose player lost their token. */
  async resetSeat(seat: number): Promise<void> {
    if (!this.host) return;
    log.info("game.seat_reset", { game_id: this.gameId, seat });
    await this.send(
      api.POST("/api/games/{game_id}/seats/{seat}/reset", {
        params: { path: { game_id: this.gameId, seat }, header: { "X-Host-Token": this.host } },
      }),
    );
  }

  /** Local multiplayer: act as another seat on this device. */
  choose(seat: number): void {
    this.seat = seat;
    this.revealed = !this.local;
    void this.refresh();
  }

  setLook(seat: number | null): void {
    this.look = seat;
    void this.refresh();
  }

  show(next: GameView): void {
    this.offset = next.server_ms - Date.now();
    const latest = this.latest;
    if (!isNewer(latest, next)) {
      // Same version: only señas may have changed. Older: a stale response, dropped.
      if (latest && next.version === latest.version) {
        this.latest = { ...latest, senas: next.senas };
        if (!this.queue.busy) this.settle(this.latest);
      } else
        log.debug("game.view_stale", {
          game_id: this.gameId,
          version: next.version,
          latest: latest?.version,
        });
      return;
    }
    if (latest && next.me !== latest.me) {
      // Another seat on this device: its own view, from now on.
      this.queue.stop();
      this.beat = null;
      this.lastStep = next.step;
      this.latest = next;
      this.settle(next);
      return;
    }
    const steps = next.steps.filter((st) => st.index > this.lastStep);
    // Arriving at the table, the moves since our last one (or the deal) play from `base`.
    if (!latest && next.base && steps.length) this.view = next.base;
    const bots = new Set(next.seats.filter((s) => s.kind === "bot").map((s) => s.seat));
    const moves = stepBeats(steps, bots);
    if (latest && next.version !== latest.version) {
      log.debug("game.view", {
        game_id: this.gameId,
        seat: this.seat,
        version: next.version,
        step: next.step,
        new_steps: steps.length,
        beats: moves.length,
        busy: this.queue.busy,
      });
    }
    this.lastStep = Math.max(this.lastStep, next.step);
    this.latest = next;
    if (moves.length) this.queue.push(moves);
    else if (!this.queue.busy) this.settle(next);
  }

  private land(b: Beat): void {
    this.thinking = false;
    // A new mano: the last one's cards leave the table as the new hands come in.
    if (b.kind === "reparto")
      this.swept = this.view?.seats.filter((s) => s.played.length).map((s) => s.seat) ?? [];
    this.view = b.view;
    const sound = sfxFor(b.kind);
    if (sound) play(sound);
  }

  private settle(next: GameView): void {
    if (this.view?.version !== next.version) {
      log.debug("game.settled", {
        game_id: this.gameId,
        version: next.version,
        to_act: next.to_act,
      });
    }
    this.view = next;
    // Local multiplayer: follow the turn to the next human on this device, behind a curtain.
    const turn = next.to_act;
    if (turn !== null && turn !== undefined && turn in this.tokens && turn !== this.seat) {
      this.seat = turn;
      if (this.local) this.revealed = false;
    }
  }

  /** Send a request answered with a view; `quiet` statuses are expected, not errors. */
  private async send(request: Promise<ApiResult<GameView>>, quiet: number[] = []) {
    const res = await this.reach(request);
    if (!res) return;
    if (res.data) {
      this.error = null;
      this.show(res.data);
    } else if (!quiet.includes(res.response.status)) this.fail(res.error, res.response.status);
  }

  // The server can't be reached (down, restarting, offline): the client already logged it
  // (api.network_error); say so until a request gets through again.
  private async reach<T>(request: Promise<T>): Promise<T | null> {
    try {
      const res = await request;
      this.offline = false;
      return res;
    } catch {
      this.offline = true;
      return null;
    }
  }

  private fail(err: unknown, status?: number): void {
    if (status === 404) {
      // The game is over and gone (evicted), or the link is wrong: go home instead of
      // polling a 404 forever.
      if (this.gone) return;
      this.gone = true;
      log.warn("game.not_found", { game_id: this.gameId });
      this.onGone();
      return;
    }
    if (status === 403 && this.seat !== null) {
      // The host freed our seat (we were away): its token is dead; watch, or join again.
      log.warn("game.seat_lost", { game_id: this.gameId, seat: this.seat });
      forgetToken(this.gameId, this.seat);
      this.tokens = loadTokens(this.gameId);
      this.seat = this.mySeats[0] ?? null;
      this.latest = null;
      this.lastStep = -1;
      this.error = t("game.seatLost");
      void this.refresh();
      return;
    }
    this.error = errorMessage(err);
    log.warn("game.error", { game_id: this.gameId, seat: this.seat, message: this.error });
  }
}
