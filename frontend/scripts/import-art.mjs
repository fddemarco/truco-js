// Imports the raster art made from docs/art-prompts.md into static/ as WebP.
// Run with `pnpm import-art` (or `pnpm import-art --partial`); the output is committed.
//
// assets/avatars/<character>/<variant>.png  ->  static/avatars/<character>/<variant>.webp
//   base + one per seña, already cut out and aligned to one 512² head frame by
//   tools/art/avatars.py, plus portrait.png: the full character for avatar selection.
// assets/cards/<name>.png  ->  static/cards/<name>.webp  (400×600)
//
// Sources may be any format sharp reads (png, jpg, webp). assets/ (repo root) is gitignored.
// Without --partial the script refuses to write anything unless every expected file is there.

import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";
import { CHARACTERS, VARIANTS } from "../src/lib/avatar/avatar.ts";
import { NUMBERS, SUITS } from "../src/lib/cards.ts";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "..", "assets");
const STATIC = join(ROOT, "static");
const EXTS = [".png", ".webp", ".jpg", ".jpeg"];
const partial = process.argv.includes("--partial");

const SQUARE = { width: 512, height: 512, fit: "contain" };
const CARD = { width: 400, height: 600, fit: "fill" };

/** Every expected image: source (relative to assets/, no extension), output name, sizing. */
const expected = [
  ...CHARACTERS.flatMap((c) => [
    ...VARIANTS.map((v) => ({
      src: `avatars/${c}/${v}`,
      name: `avatars/${c}/${v}`,
      size: SQUARE,
    })),
    {
      src: `avatars/${c}/portrait`,
      name: `avatars/${c}/portrait`,
      size: SQUARE,
      trim: true,
    },
  ]),
  ...SUITS.flatMap((s) =>
    NUMBERS.map((n) => ({ src: `cards/${n}-${s}`, name: `cards/${n}-${s}`, size: CARD })),
  ),
  ...["comodin-1", "comodin-2", "dorso"].map((n) => ({
    src: `cards/${n}`,
    name: `cards/${n}`,
    size: CARD,
  })),
];

function findSource(name) {
  for (const ext of EXTS) {
    const path = join(SRC, `${name}${ext}`);
    if (existsSync(path)) return path;
  }
  return null;
}

function listFiles(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? listFiles(join(dir, e.name)) : [join(dir, e.name)],
  );
}

const found = expected.map((e) => ({ ...e, path: findSource(e.src) }));
const missing = found.filter((e) => !e.path).map((e) => e.src);
const known = new Set(expected.map((e) => e.src));
// Only the folders the import reads: work files live in assets/work/.
const extra = [join(SRC, "avatars"), join(SRC, "cards")]
  .flatMap(listFiles)
  .map((f) => relative(SRC, f).replaceAll("\\", "/"))
  .filter((f) => !known.has(f.slice(0, -extname(f).length)));

if (extra.length) {
  console.warn(`Ignoring ${extra.length} unexpected file(s) (check the names):`);
  for (const f of extra) console.warn(`  assets/${f}`);
}
if (missing.length) {
  console.warn(`Missing ${missing.length} of ${expected.length} image(s):`);
  for (const m of missing) console.warn(`  assets/${m}.png`);
  if (!partial) {
    console.error("Nothing written. Add the missing images or run with --partial.");
    process.exit(1);
  }
}

let written = 0;
for (const { name, path, size, trim } of found) {
  if (!path) continue;
  let img = sharp(path).ensureAlpha();
  // Only the portrait is trimmed: the variants share one head frame, and trimming each one
  // separately would make the head jump between señas.
  if (trim) img = sharp(await img.trim({ threshold: 10 }).toBuffer());
  const out = join(STATIC, `${name}.webp`);
  mkdirSync(dirname(out), { recursive: true });
  await img
    .resize({ ...size, background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .webp({ quality: 88, alphaQuality: 100 })
    .toFile(out);
  written++;
}
console.log(`wrote ${written} of ${expected.length} image(s) to static/`);
