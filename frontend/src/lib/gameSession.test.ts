import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { GameView, StepView } from "$lib/api/client";

const GET = vi.fn();
const POST = vi.fn();
vi.mock("$lib/api/client", () => ({
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a) },
  errorMessage: (e: { detail?: string } | undefined) => e?.detail ?? "Request failed",
}));
vi.mock("$lib/audio.svelte", () => ({ play: vi.fn(), sfxFor: () => null }));

const { TableSession, POLL_MS } = await import("./gameSession.svelte");
const { loadTokens, saveToken } = await import("./game");

function view(over: Partial<GameView> = {}): GameView {
  return {
    id: "g1",
    version: 1,
    server_ms: Date.now(),
    me: 0,
    step: 0,
    steps: [],
    base: null,
    senas: [],
    seats: [],
    actions: [],
    deal_at: null,
    cutter: null,
    result: null,
    to_act: null,
    ...over,
  } as unknown as GameView;
}

const ok = (data: GameView) => ({ data, response: new Response(null, { status: 200 }) });
const refused = (status: number, detail = "no") => ({
  error: { detail },
  response: new Response(null, { status }),
});

beforeEach(() => {
  localStorage.clear();
  GET.mockReset();
  POST.mockReset();
});
afterEach(() => vi.useRealTimers());

describe("TableSession.show", () => {
  it("drops stale views and merges señas from the same version", () => {
    const game = new TableSession("g1", () => {});
    game.show(view({ version: 5 }));
    game.show(view({ version: 4 }));
    expect(game.view?.version).toBe(5);
    const senas = [{ seat: 3 }] as GameView["senas"];
    game.show(view({ version: 5, senas }));
    expect(game.latest?.senas).toEqual(senas);
  });

  it("replays the moves missed on arrival from `base`", () => {
    const game = new TableSession("g1", () => {});
    const deal: StepView = {
      index: 3,
      seat: null,
      events: [{ kind: "reparto", seat: null } as StepView["events"][number]],
      view: view({ version: 2 }),
    };
    game.show(view({ version: 3, step: 3, steps: [deal], base: view({ version: 1 }) }));
    expect(game.busy).toBe(true); // the deal plays as a beat
    expect(game.latest?.version).toBe(3);
  });

  it("starts over when this device switches seats", () => {
    const game = new TableSession("g1", () => {});
    game.show(view({ version: 5, me: 0 }));
    game.show(view({ version: 5, me: 2, step: 9 }));
    expect(game.view?.me).toBe(2);
    expect(game.busy).toBe(false);
  });
});

describe("TableSession transport", () => {
  it("polls every second, and not while hidden", async () => {
    vi.useFakeTimers();
    GET.mockResolvedValue(ok(view()));
    const game = new TableSession("g1", () => {});
    const stop = game.start();
    await vi.advanceTimersByTimeAsync(POLL_MS * 3);
    expect(GET).toHaveBeenCalledTimes(4); // on start, then each second
    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    await vi.advanceTimersByTimeAsync(POLL_MS * 3);
    expect(GET).toHaveBeenCalledTimes(4);
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
    stop();
  });

  it("sends the seat token as a header, never in the URL", async () => {
    saveToken("g1", 2, "secret");
    GET.mockResolvedValue(ok(view()));
    const game = new TableSession("g1", () => {});
    game.seat = 2;
    await game.refresh();
    const [, options] = GET.mock.calls[0];
    expect(options.params.header).toEqual({ "X-Seat-Token": "secret" });
    expect(JSON.stringify(options.params.query)).not.toContain("secret");
  });
});

describe("TableSession errors", () => {
  it("shows a refused move until a request goes through", async () => {
    saveToken("g1", 0, "t");
    POST.mockResolvedValue(refused(400, "not your turn"));
    const game = new TableSession("g1", () => {});
    game.seat = 0;
    await game.act({ kind: "quiero", card: null, number: null, sena: null });
    expect(game.error).toBe("not your turn");
    GET.mockResolvedValue(ok(view()));
    await game.refresh();
    expect(game.error).toBeNull();
  });

  it("forgets a seat the host freed and watches instead", async () => {
    saveToken("g1", 1, "dead");
    GET.mockResolvedValueOnce(refused(403)).mockResolvedValue(ok(view({ me: null })));
    const game = new TableSession("g1", () => {});
    game.seat = 1;
    await game.refresh();
    expect(loadTokens("g1")).toEqual({});
    expect(game.seat).toBeNull();
    expect(game.error).not.toBeNull();
    expect(GET.mock.calls[1][1].params.header).toEqual({});
  });

  it("goes home once when the game is gone", async () => {
    GET.mockResolvedValue(refused(404));
    const gone = vi.fn();
    const game = new TableSession("g1", gone);
    await game.refresh();
    await game.refresh();
    expect(gone).toHaveBeenCalledTimes(1);
  });

  it("says the server is unreachable until it answers again", async () => {
    GET.mockRejectedValueOnce(new TypeError("fetch failed")).mockResolvedValue(ok(view()));
    const game = new TableSession("g1", () => {});
    await game.refresh();
    expect(game.offline).toBe(true);
    await game.refresh();
    expect(game.offline).toBe(false);
  });
});
