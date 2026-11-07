/** Human-readable duration between two ISO timestamps (or until now). */
export function formatDuration(start: string, end?: string | null): string {
  const ms = (end ? Date.parse(end) : Date.now()) - Date.parse(start);
  if (Number.isNaN(ms) || ms < 0) return "—";
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${Math.round(s % 60)}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

/** Render a DuckDB cell value for display. */
export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "∅";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
