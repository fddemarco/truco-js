/**
 * Seat avatars with señas (reglamento Anexo C), drawn as raster sprites: one image per
 * character and variant in `static/avatars/<character>/<variant>.webp`. The art is made from
 * the prompts in `docs/art-prompts.md` and imported with `pnpm import-art`.
 *
 * Right and left are the signaller's (C.1): their right side is the viewer's left.
 * Seña and spot values match the backend's `Sena` and `BodySpot` enums.
 */

import { artUrl } from "$lib/art";

export type Sena =
  "sena_01" | "sena_02" | "sena_03" | "sena_04" | "sena_05" | "sena_06" | "sena_07" | "sena_12";

export type BodySpot =
  | "cejas"
  | "ojo_derecho"
  | "comisura_derecha"
  | "comisura_izquierda"
  | "labio_inferior"
  | "labios"
  | "boca"
  | "nariz";

/** Where each gesture is made (Anexo C.2). There is no 08–11 (C.3). */
export const SPOTS: Record<Sena, BodySpot[]> = {
  sena_01: ["cejas"],
  sena_02: ["ojo_derecho"],
  sena_03: ["comisura_derecha"],
  sena_04: ["comisura_izquierda"],
  sena_05: ["labio_inferior"],
  sena_06: ["labios"],
  sena_07: ["boca"],
  sena_12: ["nariz"],
};

export const SENAS = Object.keys(SPOTS) as Sena[];

/** What each seña means (Anexo C.2). Card names are game terms: Spanish in every locale. */
export const SENA_NAMES: Record<Sena, string> = {
  sena_01: "Ancho de espadas",
  sena_02: "Ancho de bastos",
  sena_03: "Siete bravo (7 de espadas)",
  sena_04: "Siete de oros",
  sena_05: "Un tres",
  sena_06: "Un dos",
  sena_07: "Ancho falso (1 de copas u oros)",
  sena_12: "Buen envido",
};

/** The six characters, one per seat (see `docs/art-prompts.md`). */
export const CHARACTERS = [
  "tiburon",
  "maniaca",
  "roca",
  "novato",
  "calculadora",
  "fanfarron",
] as const;

export type Character = (typeof CHARACTERS)[number];

/** Display names: proper names, the same in every language (match the backend's). */
export const CHARACTER_NAMES: Record<Character, string> = {
  tiburon: "Tiburón",
  maniaca: "Maníaca",
  roca: "Roca",
  novato: "Novato",
  calculadora: "Calculadora",
  fanfarron: "Fanfarrón",
};

export function isCharacter(value: unknown): value is Character {
  return typeof value === "string" && (CHARACTERS as readonly string[]).includes(value);
}

/** Every image name a character has: `base` and one per seña. 9 in total. */
export const VARIANTS: string[] = ["base", ...SENAS];

/** The character for a seat index (wraps around). */
export function characterFor(seat: number): Character {
  return CHARACTERS[((seat % CHARACTERS.length) + CHARACTERS.length) % CHARACTERS.length];
}

/** The variant name for a seña. Throws if `spot` is not where the seña is made. */
export function variantFor(sena?: Sena, spot?: BodySpot): string {
  if (!sena) return "base";
  if (spot && !SPOTS[sena].includes(spot)) {
    throw new Error(`${sena} is not made on the ${spot}`);
  }
  return sena;
}

export function avatarSrc(character: Character, sena?: Sena, spot?: BodySpot): string {
  return artUrl(`/avatars/${character}/${variantFor(sena, spot)}.webp`);
}

/** The full character (not cropped to the head frame), for choosing an avatar. */
export function avatarPortrait(character: Character): string {
  return artUrl(`/avatars/${character}/portrait.webp`);
}

/** All of a character's images, for preloading so a short seña never flashes blank. */
export function avatarVariants(character: Character): string[] {
  return VARIANTS.map((v) => artUrl(`/avatars/${character}/${v}.webp`));
}
