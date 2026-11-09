/**
 * URLs for the art in static/avatars and static/cards. Vercel serves those folders with a
 * year-long immutable Cache-Control (vercel.json), so every URL carries the art's version: a
 * hash of the files, computed at build time (vite.config.ts), which changes when `pnpm
 * import-art` changes any image. Empty in tests, so paths stay plain.
 */
declare const __ART_VERSION__: string;

export function artUrl(path: string): string {
  return __ART_VERSION__ ? `${path}?v=${__ART_VERSION__}` : path;
}
