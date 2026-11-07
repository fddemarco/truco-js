// Generates the Spanish deck SVGs and other static art into static/.
// Run with `pnpm gen-cards` after changing anything here; the output is committed.
//
// static/cards/<number>-<suit>.svg   1–12 of espada, basto, oro, copa (48 cards)
// static/cards/comodin-1.svg, -2     the two jokers
// static/cards/dorso.svg             card back
// static/suits/<suit>.svg            suit symbols for UI use
// static/ui/fosforo.svg              matchstick for the tally scoreboard
// static/favicon.svg, static/logo.svg

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const STATIC = join(dirname(fileURLToPath(import.meta.url)), "..", "static");

const W = 200;
const H = 300;
const INK = "#2b2b2b";
const PAPER = "#fbf7ee";
const GOLD = "#e0b43a";
const SKIN = "#f2c9a0";
const HAIR = "#5b3a1a";
const FONT = "Georgia, 'Times New Roman', serif";

const SUITS = {
  oro: { plural: "oros", color: "#c9961a", dark: "#7d5c0c", accent: "#b3261e", gaps: 0 },
  copa: { plural: "copas", color: "#b3261e", dark: "#6e140f", accent: GOLD, gaps: 1 },
  espada: { plural: "espadas", color: "#1f4e8c", dark: "#11305a", accent: GOLD, gaps: 2 },
  basto: { plural: "bastos", color: "#2e6b30", dark: "#1a421c", accent: GOLD, gaps: 3 },
};

const FIGURES = { 10: "Sota", 11: "Caballo", 12: "Rey" };

// --- suit symbols, centered at the origin, about 100 units tall ---------------------

function oro(s) {
  const rays = Array.from({ length: 8 }, (_, i) => {
    const a = (i * Math.PI) / 4;
    const [x1, y1, x2, y2] = [13, 13, 21, 21].map(
      (r, k) => (k % 2 ? Math.sin(a) : Math.cos(a)) * r,
    );
    return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${s.dark}" stroke-width="2.5" stroke-linecap="round"/>`;
  }).join("");
  return `<circle r="36" fill="${s.color}" stroke="${s.dark}" stroke-width="3"/>
<circle r="29" fill="none" stroke="${s.dark}" stroke-width="1.5" stroke-dasharray="3 3"/>
<circle r="24" fill="#e9c35a" stroke="${s.dark}" stroke-width="2"/>
${rays}<circle r="9" fill="${s.accent}" stroke="${s.dark}" stroke-width="2"/>`;
}

function copa(s) {
  return `<path d="M-24 44 Q0 30 24 44 L24 48 L-24 48 Z" fill="${s.color}" stroke="${s.dark}" stroke-width="2.5" stroke-linejoin="round"/>
<path d="M-5 10 L5 10 L6 36 L-6 36 Z" fill="${s.color}" stroke="${s.dark}" stroke-width="2.5"/>
<ellipse cy="22" rx="10" ry="4.5" fill="${GOLD}" stroke="${s.dark}" stroke-width="2"/>
<path d="M-31 -38 L31 -38 C31 -6 16 9 0 11 C-16 9 -31 -6 -31 -38 Z" fill="${s.color}" stroke="${s.dark}" stroke-width="2.5" stroke-linejoin="round"/>
<path d="M-28 -22 C-10 -16 10 -16 28 -22" fill="none" stroke="${GOLD}" stroke-width="4"/>
<circle cy="-6" r="4" fill="${GOLD}" stroke="${s.dark}" stroke-width="1.5"/>
<ellipse cy="-38" rx="31" ry="6" fill="#d9534f" stroke="${s.dark}" stroke-width="2.5"/>`;
}

function espada(s) {
  return `<path d="M0 -52 L7 -40 L7 18 L-7 18 L-7 -40 Z" fill="#d6dde6" stroke="${s.dark}" stroke-width="2.5" stroke-linejoin="round"/>
<line x1="0" y1="-38" x2="0" y2="14" stroke="#98a6b8" stroke-width="2"/>
<path d="M-26 22 C-26 14 -18 16 -14 18 L14 18 C18 16 26 14 26 22 C26 27 20 26 16 25 L-16 25 C-20 26 -26 27 -26 22 Z" fill="${s.color}" stroke="${s.dark}" stroke-width="2.5" stroke-linejoin="round"/>
<rect x="-5" y="25" width="10" height="17" fill="${s.dark}"/>
<path d="M-5 29 L5 32 M-5 34 L5 37" stroke="${GOLD}" stroke-width="1.5"/>
<circle cy="47" r="6" fill="${GOLD}" stroke="${s.dark}" stroke-width="2.5"/>`;
}

function basto(s) {
  return `<path d="M-8 49 C-11 22 -17 -8 -15 -34 C-14 -50 14 -52 15 -36 C17 -8 11 22 8 49 C4 52 -4 52 -8 49 Z" fill="#9a6a3a" stroke="#4e3115" stroke-width="2.5" stroke-linejoin="round"/>
<path d="M-6 -40 C-8 -10 -4 20 -2 44" fill="none" stroke="#b98a55" stroke-width="3" stroke-linecap="round"/>
<ellipse cx="-12" cy="-14" rx="4" ry="3" fill="#4e3115"/>
<ellipse cx="11" cy="4" rx="4" ry="3" fill="#4e3115"/>
<ellipse cx="-8" cy="24" rx="3.5" ry="2.5" fill="#4e3115"/>
<path d="M14 -24 C24 -34 34 -30 36 -26 C30 -20 22 -18 14 -24 Z" fill="${s.color}" stroke="${s.dark}" stroke-width="1.5"/>
<path d="M-13 6 C-24 0 -32 6 -33 10 C-26 14 -19 12 -13 6 Z" fill="${s.color}" stroke="${s.dark}" stroke-width="1.5"/>`;
}

const SYMBOL = { oro, copa, espada, basto };

function symbol(suit, x, y, scale, rotate = 0) {
  const r = rotate ? ` rotate(${rotate})` : "";
  return `<g transform="translate(${x} ${y}) scale(${scale})${r}">${SYMBOL[suit](SUITS[suit])}</g>`;
}

// --- card chrome: paper, frame with pintas, corner indices -------------------------

/** The frame's top and bottom edges are broken by 0–3 gaps (pintas) that tell the suit. */
function frame(suit) {
  const { gaps, color } = SUITS[suit];
  const [x0, x1, y0, y1] = [14, W - 14, 14, H - 14];
  const gap = 9;
  const centers = Array.from({ length: gaps }, (_, i) => W / 2 + (i - (gaps - 1) / 2) * 16);
  const segments = [];
  let from = x0;
  for (const c of centers) {
    segments.push([from, c - gap / 2]);
    from = c + gap / 2;
  }
  segments.push([from, x1]);
  const horizontal = (y) =>
    segments.map(([a, b]) => `<line x1="${a}" y1="${y}" x2="${b}" y2="${y}"/>`).join("");
  return `<g stroke="${color}" stroke-width="3" stroke-linecap="square">
<line x1="${x0}" y1="${y0}" x2="${x0}" y2="${y1}"/><line x1="${x1}" y1="${y0}" x2="${x1}" y2="${y1}"/>
${horizontal(y0)}${horizontal(y1)}</g>`;
}

function index(label, suit, color) {
  const corner = `<text x="27" y="44" text-anchor="middle" font-family="${FONT}" font-size="26" font-weight="bold" fill="${color}">${label}</text>${
    suit ? symbol(suit, 27, 60, 0.16) : ""
  }`;
  return `${corner}<g transform="rotate(180 ${W / 2} ${H / 2})">${corner}</g>`;
}

function svg(title, body, { width = W, height = H, viewBox = `0 0 ${W} ${H}` } = {}) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${width}" height="${height}" role="img">
<title>${title}</title>
${body}
</svg>
`;
}

function paper(fill = PAPER) {
  return `<rect x="1" y="1" width="${W - 2}" height="${H - 2}" rx="12" fill="${fill}" stroke="${INK}" stroke-width="2"/>`;
}

// --- pips for 1–9 -------------------------------------------------------------------

// Normalized positions inside the pip area (x 30..170, y 52..248).
const LAYOUTS = {
  2: [
    [0.5, 0.18],
    [0.5, 0.82],
  ],
  3: [
    [0.5, 0.14],
    [0.5, 0.5],
    [0.5, 0.86],
  ],
  4: [
    [0.28, 0.2],
    [0.72, 0.2],
    [0.28, 0.8],
    [0.72, 0.8],
  ],
  5: [
    [0.28, 0.17],
    [0.72, 0.17],
    [0.5, 0.5],
    [0.28, 0.83],
    [0.72, 0.83],
  ],
  6: [
    [0.28, 0.14],
    [0.72, 0.14],
    [0.28, 0.5],
    [0.72, 0.5],
    [0.28, 0.86],
    [0.72, 0.86],
  ],
  7: [
    [0.28, 0.12],
    [0.72, 0.12],
    [0.5, 0.32],
    [0.28, 0.54],
    [0.72, 0.54],
    [0.28, 0.88],
    [0.72, 0.88],
  ],
  8: [
    [0.28, 0.11],
    [0.72, 0.11],
    [0.28, 0.37],
    [0.72, 0.37],
    [0.28, 0.63],
    [0.72, 0.63],
    [0.28, 0.89],
    [0.72, 0.89],
  ],
  9: [
    [0.28, 0.11],
    [0.72, 0.11],
    [0.28, 0.37],
    [0.72, 0.37],
    [0.5, 0.5],
    [0.28, 0.63],
    [0.72, 0.63],
    [0.28, 0.89],
    [0.72, 0.89],
  ],
};
const PIP_SCALE = { 2: 0.62, 3: 0.52, 4: 0.55, 5: 0.5, 6: 0.48, 7: 0.42, 8: 0.4, 9: 0.38 };

function pips(n, suit) {
  if (n === 1) return ace(suit);
  // Swords and clubs are narrow, so they can be drawn larger than coins and cups.
  const narrow = suit === "espada" || suit === "basto";
  const s = PIP_SCALE[n] * (narrow ? (n >= 7 ? 1.1 : 1.2) : 1);
  return LAYOUTS[n].map(([fx, fy]) => symbol(suit, 30 + fx * 140, 52 + fy * 196, s)).join("");
}

/** Point and tangent angle (degrees) of a cubic Bézier at t. */
function bezier([p0, p1, p2, p3], t) {
  const u = 1 - t;
  const at = (k) => u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k];
  const d = (k) =>
    3 * u * u * (p1[k] - p0[k]) + 6 * u * t * (p2[k] - p1[k]) + 3 * t * t * (p3[k] - p2[k]);
  return [at(0), at(1), (Math.atan2(d(1), d(0)) * 180) / Math.PI];
}

function wreath(color) {
  const left = [
    [94, 254],
    [30, 236],
    [24, 112],
    [66, 62],
  ];
  const branch = (curve) => {
    const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = curve;
    const stem = `<path d="M${x0} ${y0} C${x1} ${y1} ${x2} ${y2} ${x3} ${y3}" fill="none" stroke="${color}" stroke-width="2"/>`;
    const leaves = Array.from({ length: 9 }, (_, i) => {
      const [x, y, angle] = bezier(curve, 0.12 + i * 0.1);
      return [-40, 40]
        .map(
          (side) =>
            `<ellipse cx="9" cy="0" rx="9" ry="3.5" transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${(angle + side).toFixed(1)})" fill="${color}"/>`,
        )
        .join("");
    }).join("");
    return stem + leaves;
  };
  const right = left.map(([x, y]) => [W - x, y]);
  return `<g opacity="0.8">${branch(left)}${branch(right)}</g>`;
}

function ace(suit) {
  const { color } = SUITS[suit];
  if (suit === "espada" || suit === "basto") {
    // The anchos, the two strongest cards of the truco, get a wreath and a bigger symbol.
    return `${wreath(color)}${symbol(suit, 100, 150, 2)}`;
  }
  return `<circle cx="100" cy="150" r="66" fill="none" stroke="${color}" stroke-width="1.5" stroke-dasharray="2 4"/>${symbol(suit, 100, 150, 1.45)}`;
}

// --- figures: sota (10), caballo (11), rey (12) -------------------------------------

function face(cx, cy, r) {
  return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${SKIN}" stroke="${INK}" stroke-width="2"/>
<circle cx="${cx - r * 0.35}" cy="${cy - r * 0.1}" r="1.6" fill="${INK}"/><circle cx="${cx + r * 0.35}" cy="${cy - r * 0.1}" r="1.6" fill="${INK}"/>
<path d="M${cx - r * 0.3} ${cy + r * 0.4} Q${cx} ${cy + r * 0.6} ${cx + r * 0.3} ${cy + r * 0.4}" fill="none" stroke="${INK}" stroke-width="1.5" stroke-linecap="round"/>`;
}

function sota(suit) {
  const { color, dark, accent } = SUITS[suit];
  return `<rect x="87" y="200" width="11" height="44" fill="${accent}" stroke="${INK}" stroke-width="2"/>
<rect x="102" y="200" width="11" height="44" fill="${accent}" stroke="${INK}" stroke-width="2"/>
<ellipse cx="90" cy="247" rx="10" ry="5" fill="${INK}"/><ellipse cx="110" cy="247" rx="10" ry="5" fill="${INK}"/>
<path d="M78 124 L122 124 L132 206 L68 206 Z" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M100 124 L100 206" stroke="${dark}" stroke-width="2"/>
<rect x="72" y="160" width="56" height="7" fill="${GOLD}" stroke="${INK}" stroke-width="1.5"/>
<path d="M78 126 L64 178 L72 180 L84 140" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<circle cx="67" cy="182" r="5" fill="${SKIN}" stroke="${INK}" stroke-width="1.5"/>
<path d="M122 126 L136 150 L130 156 L118 138" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<ellipse cx="100" cy="124" rx="16" ry="5" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
<path d="M84 96 C84 80 116 80 116 96 L116 108 L84 108 Z" fill="${HAIR}"/>
${face(100, 104, 15)}
<ellipse cx="100" cy="88" rx="22" ry="7" fill="${color}" stroke="${INK}" stroke-width="2"/>
<path d="M112 84 C124 66 136 66 140 70 C130 72 122 78 114 88 Z" fill="${accent}" stroke="${INK}" stroke-width="1.5"/>
${symbol(suit, 142, 140, 0.52)}`;
}

function caballo(suit) {
  const { color, accent } = SUITS[suit];
  const horse = "#f1ece1";
  const leg = (x) =>
    `<rect x="${x}" y="200" width="9" height="42" fill="${horse}" stroke="${INK}" stroke-width="2"/><rect x="${x - 1}" y="238" width="11" height="7" fill="${INK}"/>`;
  return `<path d="M146 182 C162 190 164 214 156 234 C154 214 150 200 140 192 Z" fill="${HAIR}" stroke="${INK}" stroke-width="1.5"/>
${leg(66)}${leg(82)}${leg(116)}${leg(132)}
<ellipse cx="102" cy="192" rx="48" ry="22" fill="${horse}" stroke="${INK}" stroke-width="2"/>
<path d="M70 196 L60 150 L42 140 L30 150 L34 158 L50 160 L56 176 L58 200 Z" fill="${horse}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M60 150 C64 160 66 178 70 192" fill="none" stroke="${HAIR}" stroke-width="5" stroke-linecap="round"/>
<path d="M50 141 L54 130 L58 143 Z" fill="${horse}" stroke="${INK}" stroke-width="1.5"/>
<circle cx="44" cy="148" r="2" fill="${INK}"/>
<path d="M34 156 L58 150" stroke="${color}" stroke-width="2"/>
<path d="M86 172 L126 172 L122 210 L90 210 Z" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M90 206 L122 206" stroke="${GOLD}" stroke-width="4"/>
<rect x="96" y="168" width="10" height="34" fill="${accent}" stroke="${INK}" stroke-width="2"/>
<path d="M90 128 L114 128 L118 174 L86 174 Z" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M114 132 L130 116 L135 121 L118 140" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
${face(102, 114, 13)}
<path d="M86 106 L118 106 L114 94 L102 88 L90 94 Z" fill="${accent}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
${symbol(suit, 142, 96, 0.46)}`;
}

function rey(suit) {
  const { color, dark, accent } = SUITS[suit];
  const ermine = Array.from(
    { length: 7 },
    (_, i) => `<path d="M100 ${140 + i * 15} l-1.5 4 h3 Z" fill="${INK}"/>`,
  ).join("");
  return `<path d="M64 248 L78 122 L122 122 L136 248 Z" fill="${dark}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M72 248 L82 128 L118 128 L128 248 Z" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<rect x="94" y="130" width="12" height="118" fill="#fff" stroke="${INK}" stroke-width="1.5"/>${ermine}
<rect x="72" y="238" width="56" height="10" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
<path d="M80 136 L66 190 L74 192 L86 152" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<circle cx="70" cy="194" r="5" fill="${SKIN}" stroke="${INK}" stroke-width="1.5"/>
<path d="M120 136 L134 160 L128 166 L116 148" fill="${color}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<ellipse cx="100" cy="124" rx="26" ry="8" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
<path d="M90 124 l-1.5 4 h3 Z M110 124 l-1.5 4 h3 Z" fill="${INK}"/>
${face(100, 102, 15)}
<path d="M85 104 C86 124 96 132 100 132 C104 132 114 124 115 104 C110 112 90 112 85 104 Z" fill="#8a6a4a" stroke="${INK}" stroke-width="1.5"/>
<path d="M84 90 L84 70 L92 80 L100 64 L108 80 L116 70 L116 90 Z" fill="${GOLD}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<circle cx="100" cy="82" r="3" fill="${accent === GOLD ? "#b3261e" : accent}"/><circle cx="90" cy="85" r="2" fill="#1f4e8c"/><circle cx="110" cy="85" r="2" fill="#1f4e8c"/>
${symbol(suit, 145, 150, 0.52)}`;
}

const FIGURE_ART = { 10: sota, 11: caballo, 12: rey };

function card(n, suit) {
  const { color, plural } = SUITS[suit];
  const art = FIGURE_ART[n] ? FIGURE_ART[n](suit) : pips(n, suit);
  const name = FIGURES[n] ? `${n} de ${plural} (${FIGURES[n].toLowerCase()})` : `${n} de ${plural}`;
  return svg(name, `${paper()}${frame(suit)}${index(n, suit, color)}${art}`);
}

// --- comodines and dorso ------------------------------------------------------------

function comodin(variant) {
  const [a, b] = variant === 1 ? ["#b3261e", GOLD] : ["#1f4e8c", "#2e6b30"];
  const bell = (x, y) =>
    `<circle cx="${x}" cy="${y}" r="5" fill="${GOLD}" stroke="${INK}" stroke-width="1.5"/>`;
  const diamonds = [0, 1, 2]
    .map(
      (i) =>
        `<path d="M${84 + i * 16} 150 l8 14 l-8 14 l-8 -14 Z" fill="${i % 2 ? a : b}" stroke="${INK}" stroke-width="1"/>`,
    )
    .join("");
  const body = `<path d="M74 132 L126 132 L138 230 L62 230 Z" fill="${b}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M100 132 L100 230 L62 230 L74 132 Z" fill="${a}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
${diamonds}
<path d="M70 132 L80 142 L90 132 L100 142 L110 132 L120 142 L130 132 L126 124 L74 124 Z" fill="#fff" stroke="${INK}" stroke-width="1.5"/>
<rect x="84" y="230" width="12" height="18" fill="${a}" stroke="${INK}" stroke-width="2"/><rect x="104" y="230" width="12" height="18" fill="${b}" stroke="${INK}" stroke-width="2"/>
<path d="M80 248 L98 248 L98 254 L74 254 Z M102 248 L120 248 L126 254 L102 254 Z" fill="${INK}"/>
<path d="M74 136 L56 176 L64 180 L80 150" fill="${a}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M126 136 L144 176 L136 180 L120 150" fill="${b}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M56 180 L52 194 L62 188 Z" fill="${INK}"/>
<rect x="140" y="160" width="4" height="40" fill="#9a6a3a" transform="rotate(-20 142 180)"/><circle cx="150" cy="158" r="8" fill="${a}" stroke="${INK}" stroke-width="1.5"/>
${face(100, 108, 15)}
<path d="M86 102 C78 82 60 74 50 82 C62 84 72 92 84 98 Z" fill="${a}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M114 102 C122 82 140 74 150 82 C138 84 128 92 116 98 Z" fill="${b}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<path d="M88 98 C88 76 100 62 104 58 C108 70 112 84 112 98 Z" fill="${variant === 1 ? b : a}" stroke="${INK}" stroke-width="2" stroke-linejoin="round"/>
<rect x="84" y="94" width="32" height="6" rx="2" fill="${GOLD}" stroke="${INK}" stroke-width="1.5"/>
${bell(50, 82)}${bell(150, 82)}${bell(104, 58)}`;
  const star = `<path d="M0 -9 L2.6 -2.8 L9 -2.8 L3.9 1.1 L5.8 7.5 L0 3.6 L-5.8 7.5 L-3.9 1.1 L-9 -2.8 L-2.6 -2.8 Z" fill="${a}"/>`;
  const corner = `<g transform="translate(27 36)">${star}</g><text x="27" y="62" text-anchor="middle" font-family="${FONT}" font-size="11" font-weight="bold" fill="${a}">C</text>`;
  const indices = `${corner}<g transform="rotate(180 ${W / 2} ${H / 2})">${corner}</g>`;
  const label = `<text x="100" y="276" text-anchor="middle" font-family="${FONT}" font-size="14" font-weight="bold" letter-spacing="3" fill="${a}">COMODÍN</text>`;
  const border = `<rect x="14" y="14" width="${W - 28}" height="${H - 28}" fill="none" stroke="${a}" stroke-width="3"/>`;
  return svg(`Comodín ${variant}`, `${paper()}${border}${indices}${body}${label}`);
}

function dorso() {
  const red = "#8e1b17";
  const medallion = ["espada", "basto", "oro", "copa"]
    .map((suit, i) => {
      const a = (i * Math.PI) / 2 - Math.PI / 2;
      return symbol(suit, 100 + Math.cos(a) * 24, 150 + Math.sin(a) * 30, 0.3);
    })
    .join("");
  return svg(
    "Dorso",
    `<defs><pattern id="rombos" width="16" height="16" patternUnits="userSpaceOnUse">
<rect width="16" height="16" fill="${red}"/><path d="M8 1 L15 8 L8 15 L1 8 Z" fill="none" stroke="${GOLD}" stroke-width="1" opacity="0.55"/>
<circle cx="8" cy="8" r="1.4" fill="${GOLD}" opacity="0.7"/></pattern></defs>
${paper("#fff")}
<rect x="10" y="10" width="${W - 20}" height="${H - 20}" rx="6" fill="url(#rombos)" stroke="${GOLD}" stroke-width="2"/>
<rect x="17" y="17" width="${W - 34}" height="${H - 34}" rx="3" fill="none" stroke="${GOLD}" stroke-width="1"/>
<ellipse cx="100" cy="150" rx="48" ry="56" fill="${PAPER}" stroke="${GOLD}" stroke-width="3"/>
<ellipse cx="100" cy="150" rx="42" ry="50" fill="none" stroke="${red}" stroke-width="1.5"/>
${medallion}`,
  );
}

// --- standalone UI art -------------------------------------------------------------

function suitIcon(suit) {
  return svg(SUITS[suit].plural, SYMBOL[suit](SUITS[suit]), {
    width: 100,
    height: 104,
    viewBox: "-52 -54 104 108",
  });
}

function fosforo() {
  return svg(
    "Fósforo",
    `<rect x="4" y="12" width="4" height="66" rx="1" fill="#e8c88a" stroke="#a07c3c" stroke-width="0.8"/>
<ellipse cx="6" cy="10" rx="4.5" ry="7" fill="#b3261e" stroke="#6e140f" stroke-width="0.8"/>`,
    { width: 12, height: 80, viewBox: "0 0 12 80" },
  );
}

function favicon() {
  return svg(
    "Truco",
    `<rect x="12" y="2" width="40" height="60" rx="5" fill="${PAPER}" stroke="${INK}" stroke-width="2.5"/>
${symbol("espada", 32, 32, 0.5)}`,
    { width: 64, height: 64, viewBox: "0 0 64 64" },
  );
}

function logo() {
  const mini = (x, rot, suit) =>
    `<g transform="rotate(${rot} ${x + 15} 66)"><rect x="${x}" y="14" width="30" height="46" rx="4" fill="${PAPER}" stroke="${INK}" stroke-width="2"/>${symbol(suit, x + 15, 37, 0.3)}</g>`;
  return svg(
    "Truco",
    `${mini(16, -16, "espada")}${mini(32, 0, "basto")}${mini(48, 16, "oro")}
<text x="96" y="50" font-family="${FONT}" font-size="36" font-weight="bold" fill="${INK}">Truco</text>`,
    { width: 200, height: 72, viewBox: "0 0 200 72" },
  );
}

// --- write -------------------------------------------------------------------------

function write(path, content) {
  const full = join(STATIC, path);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, content);
}

let count = 0;
for (const suit of Object.keys(SUITS)) {
  for (let n = 1; n <= 12; n++) {
    write(`cards/${n}-${suit}.svg`, card(n, suit));
    count++;
  }
  write(`suits/${suit}.svg`, suitIcon(suit));
}
write("cards/comodin-1.svg", comodin(1));
write("cards/comodin-2.svg", comodin(2));
write("cards/dorso.svg", dorso());
write("ui/fosforo.svg", fosforo());
write("favicon.svg", favicon());
write("logo.svg", logo());
console.log(`wrote ${count} cards + 2 comodines + dorso, suit icons, fósforo, favicon and logo`);
