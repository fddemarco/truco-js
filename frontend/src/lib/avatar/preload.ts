import { avatarVariants, type Character } from "./avatar";

/**
 * Avatar images, fetched and decoded ahead of time and held for the page's life, so the
 * browser keeps them ready to paint: a seña lasts about half a second and must never show a
 * blank or half-drawn face. The play page starts this as soon as it knows who is seated.
 */
const decoded = new Set<string>();
const loading = new Map<string, { img: HTMLImageElement; ready: Promise<void> }>();

export function isDecoded(src: string): boolean {
  return decoded.has(src);
}

/** Fetches and decodes one image; rejects if it cannot be loaded. */
export function loadImage(src: string): Promise<void> {
  let entry = loading.get(src);
  if (!entry) {
    const img = new Image();
    img.src = src;
    // Without decode() (old browsers, jsdom) there is nothing to wait for.
    const ready = typeof img.decode === "function" ? img.decode() : Promise.resolve();
    entry = { img, ready: ready.then(() => void decoded.add(src)) };
    loading.set(src, entry);
  }
  return entry.ready;
}

/** Every image of these characters (failures surface when an avatar shows them). */
export function preloadAvatars(characters: Iterable<Character>): void {
  for (const c of new Set(characters)) {
    for (const src of avatarVariants(c)) loadImage(src).catch(() => {});
  }
}
