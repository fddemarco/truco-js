import { afterEach, describe, expect, it, vi } from "vitest";
import { Logger, type Entry, type Sink } from "./log";

function sink() {
  const batches: Entry[][] = [];
  const s: Sink = { send: (_, entries) => batches.push(entries) };
  return { s, batches };
}

describe("Logger", () => {
  afterEach(() => vi.useRealTimers());

  it("records structured entries at or above its level", () => {
    const log = new Logger(null, "info", "info", false);
    log.debug("noise.debug");
    log.info("beat.start", { seat: 3, kind: "truco" });
    expect(log.buffer).toHaveLength(1);
    expect(log.buffer[0]).toMatchObject({
      level: "info",
      event: "beat.start",
      fields: { seat: 3, kind: "truco" },
    });
    expect(log.buffer[0].ts).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("keeps only the most recent entries", () => {
    const log = new Logger(null, "debug", "info", false);
    for (let i = 0; i < 600; i++) log.debug("tick", { i });
    expect(log.buffer).toHaveLength(500);
    expect(log.buffer[0].fields.i).toBe(100);
  });

  it("ships info and above in batches, after a short wait", () => {
    vi.useFakeTimers();
    const { s, batches } = sink();
    const log = new Logger(s, "debug", "info", false);
    log.debug("not.shipped");
    log.info("a");
    log.warn("b");
    expect(batches).toHaveLength(0);
    vi.advanceTimersByTime(2000);
    expect(batches).toEqual([
      [expect.objectContaining({ event: "a" }), expect.objectContaining({ event: "b" })],
    ]);
  });

  it("ships errors right away, and everything waiting on flush", () => {
    vi.useFakeTimers();
    const { s, batches } = sink();
    const log = new Logger(s, "debug", "info", false);
    log.info("before");
    log.error("ui.error", { message: "boom" });
    expect(batches[0].map((e) => e.event)).toEqual(["before", "ui.error"]);
    log.info("later");
    log.flush();
    expect(batches[1].map((e) => e.event)).toEqual(["later"]);
  });
});
