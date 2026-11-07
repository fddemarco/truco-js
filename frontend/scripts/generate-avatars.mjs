// Writes the static avatar and seña previews from src/lib/avatar/avatar.ts.
// Run with `pnpm gen-avatars` (Node strips the TypeScript types); the output is committed.
//
// static/avatars/avatar-<1..6>.svg       the six seat presets, no seña
// static/senas/<sena>.svg                each seña on the first avatar, at its first spot
// static/senas/<sena>-<spot>.svg         señas with a choice of side (wrist, elbow, shoulder)

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { avatarSvg, LOOKS, SENAS, SPOTS } from "../src/lib/avatar/avatar.ts";

const STATIC = join(dirname(fileURLToPath(import.meta.url)), "..", "static");

function write(path, content) {
  const full = join(STATIC, path);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, `${content}\n`);
}

LOOKS.forEach((look, i) => write(`avatars/avatar-${i + 1}.svg`, avatarSvg({ look })));

let senas = 0;
for (const sena of SENAS) {
  const spots = SPOTS[sena];
  write(`senas/${sena}.svg`, avatarSvg({ look: LOOKS[0], sena }));
  senas++;
  if (spots.length > 1) {
    for (const spot of spots) {
      write(`senas/${sena}-${spot}.svg`, avatarSvg({ look: LOOKS[0], sena, spot }));
      senas++;
    }
  }
}
console.log(`wrote ${LOOKS.length} avatars and ${senas} seña previews`);
