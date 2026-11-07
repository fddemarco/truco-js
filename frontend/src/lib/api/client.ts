import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

/** Typed client for the FastAPI backend. Regenerate types with `make gen-api`. */
export const api = createClient<paths>({ baseUrl: "" });

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
