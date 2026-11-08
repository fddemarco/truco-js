// Imports the raster art made from docs/art-prompts.md into static/ as WebP.
// Run with `pnpm import-art` (or `pnpm import-art --partial`); the output is committed.
//
// assets/avatars/<character>/<variant>.png  ->  static/avatars/<character>/<variant>.webp
//   base + one per seña, already cut out and aligned to one 512² head frame by
//   tools/art/avatars.py, plus portrait.png: the full character for avatar selection.
// assets/cards/<suit plural>_<NN>.svg  ->  static/cards/<n>-<suit>.webp   (400×600)
// assets/cards/dorso.svg               ->  static/cards/dorso.webp
// assets/cards/card-back.jpg           ->  static/cards/dorso.webp  (wins over dorso.svg: a
//   painted back, cropped to the card and given the cards' rounded corners)
//   The card SVGs are the source; they are served as WebP because their paper texture is an
//   SVG filter, slow to repaint with many cards on the table. Comodines are optional (truco
//   plays without them).
//
// assets/ui/{bg-room,felt,wood}.png  ->  static/ui/<name>.webp   (optional: the table has
//   gradient fallbacks)
// assets/ui/banner.jpg, pattern.jpg   ->  static/ui/<name>.webp   (optional: the home page
//   hero and the tiled page background)
// assets/audio/<name>.(ogg|mp3|wav)  ->  static/audio/<name>.ogg  (optional; needs ffmpeg).
//   Names in AUDIO below. Every sound is cleaned up on the way (see AUDIO): music is trimmed
//   of silence, faded and normalised to -16 LUFS (two passes); effects are cut to the sound itself,
//   denoised, faded and normalised to -12 LUFS, a limiter holding the peaks at -1 dBFS.
//
// Sources may be SVG or any raster sharp reads (png, jpg, webp); SVG is preferred when both
// exist. assets/ (repo root) is gitignored.
// Without --partial the script refuses to write anything unless every expected file is there.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { basename, dirname, extname, join, relative } from "node:path";
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
  {
    // The painted back (848×1264, the card on a paper background) wins over the SVG one.
    src: ["cards/card-back", "cards/dorso"],
    name: "cards/dorso",
    size: CARD,
    crop: { "cards/card-back": { left: 58, top: 53, width: 732, height: 1150 } },
  },
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
  {
    src: "ui/banner",
    name: "ui/banner",
    size: { width: 1600, height: 893, fit: "cover" },
    optional: true,
    opaque: true,
  },
  {
    src: "ui/pattern",
    name: "ui/pattern",
    size: { width: 1408, height: 768, fit: "cover" },
    optional: true,
    opaque: true,
  },
  ...["felt", "wood"].map((n) => ({
    src: `ui/${n}`,
    name: `ui/${n}`,
    size: { width: 1024, height: 1024, fit: "cover" },
    optional: true,
  })),
];

/**
 * Every sound, and how to clean it up. `trim` cuts an effect to the sound itself, in seconds of
 * the source (the windows below fit the files in assets/audio/ today; re-check them with a
 * waveform when a source changes).
 */
const AUDIO = [
  // Music: the table cycles music-*, the menus menu-*, the settings page settings.
  ...["music-1", "music-2", "menu-1", "menu-2", "menu-3", "settings"].map((name) => ({
    name,
    kind: "music",
  })),
  // A card snapped onto the table: the source is 2 s of room noise around two snaps.
  { name: "card", kind: "sfx", trim: [1.3, 1.52] },
  // The riffle itself, without the handling before and the silence after.
  { name: "shuffle", kind: "sfx", trim: [1.0, 2.15] },
  // A chime when it's the viewer's move; its long tail is faded out.
  { name: "turn", kind: "sfx", trim: [0.14, 1.8] },
];
const AUDIO_EXTS = [".ogg", ".mp3", ".wav"];

/** The first source that exists: `name` may list alternatives, best first. */
function findSource(name) {
  for (const n of [name].flat()) {
    for (const ext of EXTS) {
      const path = join(SRC, `${n}${ext}`);
      if (existsSync(path)) return { path, src: n };
    }
  }
  return null;
}

function listFiles(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? listFiles(join(dir, e.name)) : [join(dir, e.name)],
  );
}

const found = expected.map((e) => {
  const source = findSource(e.src);
  return { ...e, path: source?.path ?? null, from: source?.src };
});
const missing = found.filter((e) => !e.path && !e.optional).map((e) => [e.src].flat().at(-1));
const known = new Set(expected.flatMap((e) => [e.src].flat()));
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
/** A rounded-rectangle alpha mask: the corners of the card art (16 px at 400×600). */
const roundMask = ({ width, height }) =>
  Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="${width}" height="${height}" rx="${width * 0.04}" ry="${width * 0.04}"/></svg>`,
  );

for (const { name, path, from, size, trim, crop, opaque } of found) {
  if (!path) continue;
  // SVGs render at twice their size so the downscale stays crisp.
  let img = sharp(path, extname(path) === ".svg" ? { density: 144 } : {}).ensureAlpha();
  const box = crop?.[from];
  if (box) img = sharp(await img.extract(box).toBuffer());
  // Only the portrait is trimmed: the variants share one head frame, and trimming each one
  // separately would make the head jump between señas.
  if (trim) img = sharp(await img.trim({ threshold: 10 }).toBuffer());
  img = img.resize({ ...size, background: { r: 0, g: 0, b: 0, alpha: 0 } });
  // A cropped raster card gets the rounded corners an SVG card draws itself.
  if (box) {
    img = sharp(await img.toBuffer()).composite([{ input: roundMask(size), blend: "dest-in" }]);
  }
  const out = join(STATIC, `${name}.webp`);
  mkdirSync(dirname(out), { recursive: true });
  await (
    opaque ? img.removeAlpha().webp({ quality: 80 }) : img.webp({ quality: 88, alphaQuality: 100 })
  ).toFile(out);
  written++;
}
console.log(`wrote ${written} of ${expected.length} image(s) to static/`);

// Audio is optional: a missing sound stays silent.
const ffmpeg = (args) => spawnSync("ffmpeg", ["-hide_banner", "-y", ...args], { encoding: "utf8" });
const QUIET = "silenceremove=start_periods=1:start_threshold=-50dB";
/** Fade the end: reverse, fade in, reverse back (the length isn't known up front). */
const fadeOut = (s) => `areverse,afade=t=in:d=${s},areverse`;

function cleanup({ kind, trim }) {
  if (kind === "music") {
    // Trim silence at both ends, fade, and even out the loudness between tracks.
    return [QUIET, "areverse", QUIET, "areverse", "afade=t=in:d=0.3", fadeOut(1.5)].join(",");
  }
  // Effects: cut to the sound, take out rumble and hiss, and soften the edges.
  return [
    ...(trim ? [`atrim=${trim[0]}:${trim[1]}`, "asetpts=PTS-STARTPTS"] : [QUIET]),
    "highpass=f=90",
    "afftdn=nf=-55",
    "afade=t=in:d=0.004",
    fadeOut(trim ? Math.min(0.6, (trim[1] - trim[0]) / 3) : 0.05),
  ].join(",");
}

/**
 * Music loudness, in two passes: measure, then normalise linearly to -16 LUFS. One pass
 * misses the target on tracks with a wide dynamic range (it compresses as it goes).
 */
function musicLoudness(file) {
  const target = "I=-16:TP=-1.5:LRA=20";
  const out = ffmpeg([
    "-i",
    file,
    "-af",
    `loudnorm=${target}:print_format=json`,
    "-f",
    "null",
    "-",
  ]).stderr;
  const m = JSON.parse(out.slice(out.lastIndexOf("{"), out.lastIndexOf("}") + 1));
  return (
    `loudnorm=${target}:linear=true:measured_I=${m.input_i}:measured_TP=${m.input_tp}` +
    `:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}`
  );
}

/**
 * The gain (dB) that brings an effect to -12 LUFS. Its peaks may pass -1 dBFS by up to 4 dB:
 * a limiter then holds them there (a short, transient sound is otherwise too quiet).
 */
function effectGain(file) {
  const out = ffmpeg(["-i", file, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr;
  const loud = Number(
    out
      .match(/I:\s+(-?[\d.]+) LUFS/g)
      ?.at(-1)
      ?.match(/-?[\d.]+/)?.[0],
  );
  const peak = Number(
    out
      .match(/Peak:\s+(-?[\d.]+) dBFS/g)
      ?.at(-1)
      ?.match(/-?[\d.]+/)?.[0],
  );
  const byPeak = -1 - (Number.isFinite(peak) ? peak : -1) + 4;
  // Very short sounds have no integrated loudness (-70): go by the peak alone.
  return Number.isFinite(loud) && loud > -70 ? Math.min(-12 - loud, byPeak) : byPeak;
}

let sounds = 0;
for (const sound of AUDIO) {
  const { name, kind } = sound;
  const path = AUDIO_EXTS.map((ext) => join(SRC, "audio", `${name}${ext}`)).find(existsSync);
  if (!path) continue;
  const out = join(STATIC, "audio", `${name}.ogg`);
  mkdirSync(dirname(out), { recursive: true });
  const work = join(SRC, "work", "audio", `${name}.wav`);
  mkdirSync(dirname(work), { recursive: true });
  let res = ffmpeg(["-loglevel", "error", "-i", path, "-af", cleanup(sound), "-ar", "44100", work]);
  if (res.status === 0) {
    const level =
      kind === "music"
        ? musicLoudness(work)
        : `volume=${effectGain(work).toFixed(2)}dB,alimiter=limit=0.89:level=false`;
    res = ffmpeg([
      ...["-loglevel", "error", "-i", work, "-af", level, "-ar", "44100"],
      ...["-c:a", "libvorbis", "-q:a", kind === "music" ? "4" : "6", out],
    ]);
  }
  if (res.status !== 0) {
    console.warn(
      `  could not convert assets/audio/${basename(path)}: ${res.stderr?.trim() || "is ffmpeg installed?"}`,
    );
    continue;
  }
  sounds++;
}
console.log(`wrote ${sounds} of ${AUDIO.length} sound(s) to static/audio/`);
