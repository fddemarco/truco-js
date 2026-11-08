// Imports the raster art made from docs/art-prompts.md into static/ as WebP.
// Run with `pnpm import-art` (or `pnpm import-art --partial`); the output is committed.
//
// assets/avatars/<character>/<variant>.png  ->  static/avatars/<character>/<variant>.webp
//   base + one per seña, already cut out and aligned to one 512² head frame by
//   tools/art/avatars.py, plus portrait.png: the full character for avatar selection.
// assets/cards/<suit plural>_<NN>.svg  ->  static/cards/<n>-<suit>.webp   (400×600)
// assets/cards/dorso.svg               ->  static/cards/dorso.webp
//   The card SVGs are the source; they are served as WebP because their paper texture is an
//   SVG filter, slow to repaint with many cards on the table. Comodines are optional (truco
//   plays without them).
//
// assets/ui/{bg-room,felt,wood}.png  ->  static/ui/<name>.webp   (optional: the table has
//   gradient fallbacks)
// assets/audio/<name>.(ogg|mp3|wav)  ->  static/audio/<name>.ogg  (optional; mp3/wav need
//   ffmpeg). Names: music-1, music-2, card, shuffle, cut, deal, fosforo, ronda, win, click.
//
// Sources may be SVG or any raster sharp reads (png, jpg, webp); SVG is preferred when both
// exist. assets/ (repo root) is gitignored.
// Without --partial the script refuses to write anything unless every expected file is there.

import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";
import { CHARACTERS, VARIANTS } from "../src/lib/avatar/avatar.ts";
import { NUMBERS, SUITS } from "../src/lib/cards.ts";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "..", "assets");
const STATIC = join(ROOT, "static");
const EXTS = [".svg", ".png", ".webp", ".jpg", ".jpeg"];
const PLURAL = { espada: "espadas", basto: "bastos", oro: "oros", copa: "copas" };
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
    NUMBERS.map((n) => ({
      src: `cards/${PLURAL[s]}_${String(n).padStart(2, "0")}`,
      name: `cards/${n}-${s}`,
      size: CARD,
    })),
  ),
  { src: "cards/dorso", name: "cards/dorso", size: CARD },
  ...["comodin-1", "comodin-2"].map((n) => ({
    src: `cards/${n}`,
    name: `cards/${n}`,
    size: CARD,
    optional: true,
  })),
  {
    src: "ui/bg-room",
    name: "ui/bg-room",
    size: { width: 1920, height: 1080, fit: "cover" },
    optional: true,
  },
  ...["felt", "wood"].map((n) => ({
    src: `ui/${n}`,
    name: `ui/${n}`,
    size: { width: 1024, height: 1024, fit: "cover" },
    optional: true,
  })),
];

const AUDIO = [
  "music-1",
  "music-2",
  "card",
  "shuffle",
  "cut",
  "deal",
  "fosforo",
  "ronda",
  "win",
  "click",
];
const AUDIO_EXTS = [".ogg", ".mp3", ".wav"];

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
const missing = found.filter((e) => !e.path && !e.optional).map((e) => e.src);
const known = new Set(expected.map((e) => e.src));
// Only the folders the import reads: work files live in assets/work/.
const extra = [join(SRC, "avatars"), join(SRC, "cards"), join(SRC, "ui")]
  .flatMap(listFiles)
  .map((f) => relative(SRC, f).replaceAll("\\", "/"))
  .filter((f) => !known.has(f.slice(0, -extname(f).length)));

if (extra.length) {
  console.warn(`Ignoring ${extra.length} unexpected file(s) (check the names):`);
  for (const f of extra) console.warn(`  assets/${f}`);
}
if (missing.length) {
  console.warn(`Missing ${missing.length} of ${expected.length} image(s):`);
  for (const m of missing) console.warn(`  assets/${m}.(svg|png)`);
  if (!partial) {
    console.error("Nothing written. Add the missing images or run with --partial.");
    process.exit(1);
  }
}

let written = 0;
for (const { name, path, size, trim } of found) {
  if (!path) continue;
  // SVGs render at twice their size so the downscale stays crisp.
  let img = sharp(path, extname(path) === ".svg" ? { density: 144 } : {}).ensureAlpha();
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

// Audio is optional: a missing sound stays silent.
let sounds = 0;
for (const name of AUDIO) {
  const path = AUDIO_EXTS.map((ext) => join(SRC, "audio", `${name}${ext}`)).find(existsSync);
  if (!path) continue;
  const out = join(STATIC, "audio", `${name}.ogg`);
  mkdirSync(dirname(out), { recursive: true });
  if (extname(path) === ".ogg") {
    copyFileSync(path, out);
  } else {
    const res = spawnSync("ffmpeg", [
      "-y",
      "-loglevel",
      "error",
      "-i",
      path,
      "-c:a",
      "libvorbis",
      "-q:a",
      "5",
      out,
    ]);
    if (res.status !== 0) {
      console.warn(
        `  could not convert assets/audio/${name}${extname(path)} (is ffmpeg installed?)`,
      );
      continue;
    }
  }
  sounds++;
}
console.log(`wrote ${sounds} of ${AUDIO.length} sound(s) to static/audio/`);
