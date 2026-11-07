/**
 * Toon avatars with subtle señas (reglamento Anexo C). Pure string rendering, shared by the
 * `Avatar` component and `scripts/generate-avatars.mjs` (which writes the static previews).
 *
 * Right and left are the signaller's (C.1): their right side is the viewer's left.
 * Seña and spot values match the backend's `Sena` and `BodySpot` enums.
 */

export type Sena =
  | "sena_01"
  | "sena_02"
  | "sena_03"
  | "sena_04"
  | "sena_05"
  | "sena_06"
  | "sena_07"
  | "sena_08"
  | "sena_09"
  | "sena_10"
  | "sena_11"
  | "sena_12";

export type BodySpot =
  | "cejas"
  | "ojo_derecho"
  | "ojos"
  | "comisura_derecha"
  | "comisura_izquierda"
  | "labio_inferior"
  | "labios"
  | "boca"
  | "nariz"
  | "muneca_derecha"
  | "muneca_izquierda"
  | "codo_derecho"
  | "codo_izquierdo"
  | "hombro_derecho"
  | "hombro_izquierdo";

/** Where each gesture can be made (Anexo C.2). */
export const SPOTS: Record<Sena, BodySpot[]> = {
  sena_01: ["cejas"],
  sena_02: ["ojo_derecho"],
  sena_03: ["comisura_derecha"],
  sena_04: ["comisura_izquierda"],
  sena_05: ["labio_inferior"],
  sena_06: ["labios"],
  sena_07: ["boca"],
  sena_08: ["muneca_derecha", "muneca_izquierda"],
  sena_09: ["codo_derecho", "codo_izquierdo"],
  sena_10: ["hombro_derecho", "hombro_izquierdo"],
  sena_11: ["ojos"],
  sena_12: ["nariz"],
};

export const SENAS = Object.keys(SPOTS) as Sena[];

export interface Look {
  skin: string;
  hair: string;
  hairStyle: "corto" | "largo" | "rulos";
  shirt: string;
}

/** Six presets, one per seat. */
export const LOOKS: Look[] = [
  { skin: "#f2c9a0", hair: "#3b2a1a", hairStyle: "corto", shirt: "#3f6fb5" },
  { skin: "#c68a5c", hair: "#1f1a17", hairStyle: "rulos", shirt: "#c0503a" },
  { skin: "#e8b48a", hair: "#a0522d", hairStyle: "largo", shirt: "#4f8a4b" },
  { skin: "#8d5a3b", hair: "#141414", hairStyle: "corto", shirt: "#d19a2a" },
  { skin: "#f6d7b8", hair: "#d9b44a", hairStyle: "largo", shirt: "#7a4f9a" },
  { skin: "#b07850", hair: "#5a3a22", hairStyle: "rulos", shirt: "#2f8f8a" },
];

export interface AvatarOptions {
  look: Look;
  sena?: Sena;
  /** Defaults to the gesture's first allowed spot. */
  spot?: BodySpot;
}

const INK = "#2b2b2b";
const STYLE = `<style>@media (prefers-reduced-motion: no-preference){.sena{animation:sena-in .14s ease-out}}@keyframes sena-in{from{opacity:0}}</style>`;

const HAIR: Record<Look["hairStyle"], (color: string) => string> = {
  corto: (c) =>
    `<path d="M32 52 C30 30 46 22 60 22 C76 22 90 30 88 52 C82 40 70 36 60 38 C50 36 38 40 32 52 Z" fill="${c}" stroke="${INK}" stroke-width="2"/>`,
  largo: (c) =>
    `<path d="M30 82 C24 50 34 24 60 24 C86 24 96 50 90 82 L84 82 C86 60 80 44 60 42 C40 44 34 60 36 82 Z" fill="${c}" stroke="${INK}" stroke-width="2"/>`,
  rulos: (c) =>
    [
      [37, 42, 8],
      [46, 32, 9],
      [60, 28, 10],
      [74, 32, 9],
      [83, 42, 8],
    ]
      .map(
        ([x, y, r]) =>
          `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}" stroke="${INK}" stroke-width="2"/>`,
      )
      .join(""),
};

const FRINGE = (c: string) =>
  `<path d="M33 50 C32 32 46 26 60 26 C74 26 88 32 87 50 C80 42 72 40 64 44 C56 38 42 40 33 50 Z" fill="${c}" stroke="${INK}" stroke-width="2"/>`;

// Hand positions for touches. The other hand reaches across.
const TOUCH: Partial<Record<BodySpot, { at: [number, number]; from: [number, number] }>> = {
  muneca_derecha: { at: [41, 131], from: [86, 122] },
  muneca_izquierda: { at: [79, 131], from: [34, 122] },
  codo_derecho: { at: [25, 126], from: [86, 122] },
  codo_izquierdo: { at: [95, 126], from: [34, 122] },
  hombro_derecho: { at: [37, 106], from: [86, 122] },
  hombro_izquierdo: { at: [83, 106], from: [34, 122] },
};

const sena = (svg: string) => `<g class="sena">${svg}</g>`;

function eye(x: number, part: string, closed: boolean): string {
  return closed
    ? sena(
        `<path data-part="${part}" data-state="cerrado" d="M${x - 3.5} 57.5 Q${x} 60.5 ${x + 3.5} 57.5" fill="none" stroke="${INK}" stroke-width="2" stroke-linecap="round"/>`,
      )
    : `<ellipse data-part="${part}" data-state="abierto" cx="${x}" cy="57" rx="3" ry="3.6" fill="${INK}"/>`;
}

function mouth(spot: BodySpot | undefined): string {
  const line = (d: string) =>
    `<path d="${d}" fill="none" stroke="${INK}" stroke-width="2" stroke-linecap="round"/>`;
  switch (spot) {
    case "comisura_derecha":
      return sena(`<g data-part="boca" data-state="${spot}">${line("M49 74 Q57 79 66 76")}</g>`);
    case "comisura_izquierda":
      return sena(`<g data-part="boca" data-state="${spot}">${line("M54 76 Q63 79 71 74")}</g>`);
    case "labio_inferior":
      return sena(
        `<g data-part="boca" data-state="${spot}">${line("M53 75 L67 75")}<rect x="56" y="75" width="8" height="2.6" rx="1" fill="#fff" stroke="${INK}" stroke-width="1"/></g>`,
      );
    case "labios":
      return sena(
        `<ellipse data-part="boca" data-state="${spot}" cx="60" cy="76" rx="3" ry="2.6" fill="#c0504d" stroke="${INK}" stroke-width="1.2"/>`,
      );
    case "boca":
      return sena(
        `<ellipse data-part="boca" data-state="${spot}" cx="60" cy="76" rx="3.6" ry="2.8" fill="${INK}"/>`,
      );
    default:
      return `<g data-part="boca" data-state="sonrisa">${line("M52 75 Q60 80 68 75")}</g>`;
  }
}

function cards(): string {
  return [-12, 0, 12]
    .map(
      (r) =>
        `<rect x="54" y="106" width="12" height="18" rx="2" fill="#8e1b17" stroke="#e0b43a" stroke-width="1" transform="rotate(${r} 60 124)"/>`,
    )
    .join("");
}

function hand(x: number, y: number, look: Look, attrs = ""): string {
  return `<circle ${attrs} cx="${x}" cy="${y}" r="6" fill="${look.skin}" stroke="${INK}" stroke-width="2"/>`;
}

/** The avatar's SVG markup, viewBox 0 0 120 140. Throws if `spot` doesn't fit the seña. */
export function avatarSvg({ look, sena: s, spot }: AvatarOptions): string {
  if (s && spot && !SPOTS[s].includes(spot)) {
    throw new Error(`${s} is not made on the ${spot}`);
  }
  const at = s ? (spot ?? SPOTS[s][0]) : undefined;
  const touch = at ? TOUCH[at] : undefined;
  // The signaller's right hand is on the viewer's left.
  const reachingRight = touch !== undefined && touch.from[0] < 60;

  const brows = `<g data-part="cejas" data-state="${at === "cejas" ? "arriba" : "normal"}" fill="none" stroke="${INK}" stroke-width="2" stroke-linecap="round"><path d="M44 48 Q49 45 54 48"/><path d="M66 48 Q71 45 76 48"/></g>`;
  const nose = `<path d="M60 60 Q63.5 66 59 67" fill="none" stroke="${INK}" stroke-width="1.6" stroke-linecap="round"/>`;
  const wrinkle = sena(
    `<path data-part="nariz" data-state="arrugada" d="M56.5 57 l2.2 1.6 M63.5 57 l-2.2 1.6" stroke="${INK}" stroke-width="1.2" stroke-linecap="round"/>`,
  );

  const body = [
    `<path d="M18 140 C18 112 34 100 60 100 C86 100 102 112 102 140 Z" fill="${look.shirt}" stroke="${INK}" stroke-width="2"/>`,
    `<rect x="53" y="82" width="14" height="20" rx="4" fill="${look.skin}" stroke="${INK}" stroke-width="2"/>`,
    look.hairStyle === "largo" ? HAIR.largo(look.hair) : "",
    `<circle cx="32" cy="58" r="5" fill="${look.skin}" stroke="${INK}" stroke-width="2"/>`,
    `<circle cx="88" cy="58" r="5" fill="${look.skin}" stroke="${INK}" stroke-width="2"/>`,
    `<circle cx="60" cy="56" r="28" fill="${look.skin}" stroke="${INK}" stroke-width="2"/>`,
    look.hairStyle === "largo" ? FRINGE(look.hair) : HAIR[look.hairStyle](look.hair),
    `<circle cx="44" cy="67" r="4" fill="#e0707a" opacity="0.25"/><circle cx="76" cy="67" r="4" fill="#e0707a" opacity="0.25"/>`,
    at === "cejas" ? sena(`<g transform="translate(0 -3.5)">${brows}</g>`) : brows,
    eye(49, "ojo-derecho", at === "ojo_derecho" || at === "ojos"),
    eye(71, "ojo-izquierdo", at === "ojos"),
    nose,
    at === "nariz" ? wrinkle : "",
    mouth(at),
    cards(),
    reachingRight ? "" : hand(48, 125, look, `data-part="mano-derecha"`),
    touch && !reachingRight ? "" : hand(72, 125, look, `data-part="mano-izquierda"`),
  ];
  if (touch) {
    const part = reachingRight ? "mano-derecha" : "mano-izquierda";
    const [fx, fy] = touch.from;
    const [x, y] = touch.at;
    body.push(
      sena(
        `<path d="M${fx} ${fy} L${x} ${y}" stroke="${INK}" stroke-width="12" stroke-linecap="round"/><path d="M${fx} ${fy} L${x} ${y}" stroke="${look.shirt}" stroke-width="8" stroke-linecap="round"/>${hand(x, y, look, `data-part="${part}" data-touch="${at}"`)}`,
      ),
    );
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 140" data-sena="${s ?? ""}">${STYLE}${body.join("")}</svg>`;
}
