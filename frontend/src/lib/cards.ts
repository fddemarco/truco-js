/**
 * Card art in static/ (imported with `pnpm import-art`; suit icons from `pnpm gen-cards`). Suits match the backend's `Suit` values.
 * Card names are game terms, so they stay in Spanish in every locale.
 */
export type Suit = "espada" | "basto" | "oro" | "copa";

export const SUITS: Suit[] = ["espada", "basto", "oro", "copa"];
/** Every number with art: the full 48-card Spanish deck. */
export const NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] as const;
/** The 40 cards used in truco: no 8s, 9s or comodines (5.1). */
export const TRUCO_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12] as const;

export const CARD_BACK = "/cards/dorso.webp";
export const COMODINES = ["/cards/comodin-1.webp", "/cards/comodin-2.webp"] as const;
export const LOGO = "/logo.svg";

const PLURAL: Record<Suit, string> = {
  espada: "espadas",
  basto: "bastos",
  oro: "oros",
  copa: "copas",
};

export function cardSrc(number: number, suit: Suit): string {
  return `/cards/${number}-${suit}.webp`;
}

export function suitSrc(suit: Suit): string {
  return `/suits/${suit}.svg`;
}

const SPECIAL_RANKS: Record<string, number> = {
  "1-espada": 14,
  "1-basto": 13,
  "7-espada": 12,
  "7-oro": 11,
};
const RANK_BY_NUMBER: Record<number, number> = {
  3: 10,
  2: 9,
  1: 8,
  12: 7,
  11: 6,
  10: 5,
  7: 4,
  6: 3,
  5: 2,
  4: 1,
};

/** Truco hierarchy (Anexo A): 14 = 1 de espadas … 1 = any 4. Matches the backend's `rank`. */
export function trucoRank(number: number, suit: string): number {
  return SPECIAL_RANKS[`${number}-${suit}`] ?? RANK_BY_NUMBER[number] ?? 0;
}

/** "1 de espadas", "12 de copas". */
export function cardName(number: number, suit: Suit): string {
  return `${number} de ${PLURAL[suit]}`;
}
