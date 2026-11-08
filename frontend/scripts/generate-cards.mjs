// Generates the suit symbols and small UI art into static/.
// Run with `pnpm gen-cards` after changing anything here; the output is committed.
// The cards themselves are raster art: see docs/art-prompts.md and `pnpm import-art`.
//
// static/suits/<suit>.svg            suit symbols for UI use
// static/ui/fosforo.svg              matchstick for the tally scoreboard
// static/ui/bot.svg                  robot badge for bot seats
// static/favicon.svg, static/logo.svg

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const STATIC = join(dirname(fileURLToPath(import.meta.url)), "..", "static");

const INK = "#2b2b2b";
const PAPER = "#fbf7ee";
const GOLD = "#e0b43a";
const FONT = "Georgia, 'Times New Roman', serif";

const SUITS = {
  oro: { plural: "oros", color: "#c9961a", dark: "#7d5c0c", accent: "#b3261e" },
  copa: { plural: "copas", color: "#b3261e", dark: "#6e140f", accent: GOLD },
  espada: { plural: "espadas", color: "#1f4e8c", dark: "#11305a", accent: GOLD },
  basto: { plural: "bastos", color: "#2e6b30", dark: "#1a421c", accent: GOLD },
};

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

function svg(title, body, { width, height, viewBox }) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${width}" height="${height}" role="img">
<title>${title}</title>
${body}
</svg>
`;
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

function bot() {
  // A robot head in the table's amber, on a dark disc so it reads over any portrait.
  return svg(
    "Bot",
    `<circle cx="16" cy="16" r="15.5" fill="#1e293b" stroke="#0f172a"/>
<line x1="16" y1="5" x2="16" y2="9" stroke="#fcd34d" stroke-width="2" stroke-linecap="round"/>
<circle cx="16" cy="4.5" r="1.8" fill="#fcd34d"/>
<rect x="7.5" y="9.5" width="17" height="13" rx="3.5" fill="none" stroke="#fcd34d" stroke-width="2"/>
<circle cx="12.5" cy="15.5" r="1.8" fill="#fcd34d"/>
<circle cx="19.5" cy="15.5" r="1.8" fill="#fcd34d"/>
<line x1="5" y1="15.5" x2="7.5" y2="15.5" stroke="#fcd34d" stroke-width="2" stroke-linecap="round"/>
<line x1="24.5" y1="15.5" x2="27" y2="15.5" stroke="#fcd34d" stroke-width="2" stroke-linecap="round"/>
<line x1="12.5" y1="25.5" x2="19.5" y2="25.5" stroke="#fcd34d" stroke-width="2" stroke-linecap="round"/>`,
    { width: 32, height: 32, viewBox: "0 0 32 32" },
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

for (const suit of Object.keys(SUITS)) write(`suits/${suit}.svg`, suitIcon(suit));
write("ui/fosforo.svg", fosforo());
write("ui/bot.svg", bot());
write("favicon.svg", favicon());
write("logo.svg", logo());
console.log("wrote suit icons, fósforo, bot, favicon and logo");
