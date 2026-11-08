import createClient from "openapi-fetch";
import { log, requestId } from "$lib/log";
import type { components, paths } from "./schema";

/** Typed client for the FastAPI backend. Regenerate types with `make gen-api`. */
export const api = createClient<paths>({ baseUrl: "" });

// Tracing: each call carries its own X-Request-ID, which the backend binds to every line it
// logs for the request, and the call is logged here with the same id.
const started = new WeakMap<Request, number>();
api.use({
  onRequest({ request }) {
    request.headers.set("X-Request-ID", requestId());
    started.set(request, performance.now());
    return request;
  },
  onResponse({ request, response }) {
    const fields = {
      method: request.method,
      path: new URL(request.url, "http://x").pathname,
      status: response.status,
      duration_ms: Math.round(performance.now() - (started.get(request) ?? performance.now())),
      request_id: request.headers.get("X-Request-ID"),
    };
    // Polling a game is constant: only its failures are worth more than debug.
    if (response.status >= 500) log.error("api.request", fields);
    else if (response.status >= 400) log.warn("api.request", fields);
    else if (request.method === "GET") log.debug("api.request", fields);
    else log.info("api.request", fields);
    return response;
  },
  onError({ request, error }) {
    log.error("api.network_error", {
      method: request.method,
      path: new URL(request.url, "http://x").pathname,
      request_id: request.headers.get("X-Request-ID"),
      message: error instanceof Error ? error.message : String(error),
    });
  },
});

export type Schemas = components["schemas"];

/** Pull a readable message out of a FastAPI error body. */
export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg ?? String(d)).join("; ");
  }
  return "Request failed";
}

export type BotSettings = Schemas["BotSettings-Output"];
export type BotPreset = Schemas["BotPreset"];
export type BotConfig = Schemas["BotConfigRead"];
export type CardOrder = Schemas["CardOrder"];
export type Policy = Schemas["Policy"];
export type EnvidoCall = Schemas["EnvidoCall"];

export type GameView = Schemas["GameView"];
export type GameAction = Schemas["ActionModel-Output"];
export type ActionKind = Schemas["ActionKind"];
export type SeatView = Schemas["SeatView"];
export type SeatSetup = Schemas["SeatSetup"];
export type GameEvent = Schemas["EventView"];
export type StepView = Schemas["StepView"];
export type SenaView = Schemas["SenaView"];
export type CardModel = Schemas["CardModel"];
export type RuleMode = Schemas["RuleMode"];
export type ScoringInfo = Schemas["ScoringInfo"];
export type ChainInfo = Schemas["ChainInfo"];
export type ChainSetup = Schemas["ChainSetup"];
export type ScoringSetup = Schemas["ScoringSetup"];
