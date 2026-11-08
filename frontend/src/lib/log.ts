/**
 * Structured logging for the browser, mirroring the backend's (`app/observability.py`):
 * every entry is an event name (`area.what`) plus flat fields, never a sentence.
 *
 * - Entries go to the console in development, and to a ring buffer of the last 500
 *   (`window.__trucoLogs` in the devtools) everywhere.
 * - Entries at `info` and above are shipped in batches to `POST /api/logs`, where they join the
 *   backend log (`data/logs/app.jsonl`) with `source="frontend"` and this tab's `session_id`.
 * - Each API call carries a fresh `X-Request-ID` (see `$lib/api/client`), logged on both
 *   sides, so a frontend entry can be traced to the backend lines it caused.
 *
 * Levels: set `localStorage["log:level"]` to debug | info | warn | error (default: debug in
 * development, info otherwise).
 */

export type Level = "debug" | "info" | "warn" | "error";
export type Fields = Record<string, string | number | boolean | null | undefined>;

export interface Entry {
  ts: string;
  level: Level;
  event: string;
  fields: Fields;
}

const RANK: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const BUFFER = 500;
const BATCH = 50;
const FLUSH_MS = 2000;

function newId(): string {
  try {
    return crypto.randomUUID().replaceAll("-", "").slice(0, 16);
  } catch {
    return Math.random().toString(16).slice(2, 18);
  }
}

/** This tab's id: every entry it ships carries it. */
const sessionId = newId();
export { newId as requestId };

function configuredLevel(): Level {
  try {
    const stored = localStorage.getItem("log:level");
    if (stored && stored in RANK) return stored as Level;
  } catch {
    // Storage unavailable: use the default.
  }
  return import.meta.env.DEV ? "debug" : "info";
}

export interface Sink {
  send(sessionId: string, entries: Entry[]): void;
}

/** Ships batches with fetch (keepalive, so a batch sent while the page closes still goes). */
const httpSink: Sink = {
  send(session, entries) {
    void fetch("/api/logs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ session_id: session, entries }),
      keepalive: true,
    }).catch(() => {
      // The backend is down: the entries stay in the ring buffer and the console.
    });
  },
};

export class Logger {
  readonly buffer: Entry[] = [];
  private outbox: Entry[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private sink: Sink | null = httpSink,
    private level: Level = configuredLevel(),
    private ship: Level = "info",
    private console = import.meta.env.DEV,
  ) {}

  debug(event: string, fields: Fields = {}) {
    this.log("debug", event, fields);
  }
  info(event: string, fields: Fields = {}) {
    this.log("info", event, fields);
  }
  warn(event: string, fields: Fields = {}) {
    this.log("warn", event, fields);
  }
  error(event: string, fields: Fields = {}) {
    this.log("error", event, fields);
  }

  log(level: Level, event: string, fields: Fields = {}) {
    if (RANK[level] < RANK[this.level]) return;
    const entry: Entry = { ts: new Date().toISOString(), level, event, fields };
    this.buffer.push(entry);
    if (this.buffer.length > BUFFER) this.buffer.splice(0, this.buffer.length - BUFFER);
    if (this.console) {
      const out =
        level === "debug" ? console.debug : level === "info" ? console.info : console[level];
      out(`[${event}]`, fields);
    }
    if (this.sink && RANK[level] >= RANK[this.ship]) {
      this.outbox.push(entry);
      if (this.outbox.length >= BATCH || level === "error") this.flush();
      else this.timer ??= setTimeout(() => this.flush(), FLUSH_MS);
    }
  }

  /** Send what is waiting now (also on page hide). */
  flush() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    if (!this.sink || !this.outbox.length) return;
    const batch = this.outbox.splice(0, BATCH);
    this.sink.send(sessionId, batch);
    if (this.outbox.length) this.flush();
  }
}

export const log = new Logger();

/** Uncaught errors and rejections are logged with their stack; batches flush on page hide. */
export function installGlobalHandlers(target: Window = window) {
  target.addEventListener("error", (e) => {
    log.error("ui.error", {
      message: e.message,
      file: e.filename,
      line: e.lineno,
      stack: e.error instanceof Error ? e.error.stack : undefined,
    });
  });
  target.addEventListener("unhandledrejection", (e) => {
    const reason = e.reason;
    log.error("ui.unhandled_rejection", {
      message: reason instanceof Error ? reason.message : String(reason),
      stack: reason instanceof Error ? reason.stack : undefined,
    });
  });
  target.addEventListener("pagehide", () => log.flush());
  (target as unknown as { __trucoLogs: Entry[] }).__trucoLogs = log.buffer;
}
