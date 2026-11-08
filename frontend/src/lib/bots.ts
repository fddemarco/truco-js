import type { BotSettings, CardOrder, EnvidoCall, Policy } from "$lib/api/client";
import type { Character } from "$lib/avatar/avatar";

/** A bot as the editor saves it. `character: null`: whichever is free at the table. */
export interface BotDraft {
  name: string;
  character: Character | null;
  settings: BotSettings;
}

export const CARD_ORDERS: CardOrder[] = [
  "strongest_first",
  "weakest_first",
  "cheapest_winner",
  "random",
];
export const POLICIES: Policy[] = ["always", "never", "threshold"];
export const ENVIDO_CALLS: EnvidoCall[] = ["envido", "real_envido", "falta_envido"];

/** Truco thresholds are ranks on the hierarchy (Anexo A); card names are game terms. */
export const RANKS: { rank: number; label: string }[] = [
  { rank: 14, label: "1 de espadas" },
  { rank: 13, label: "1 de bastos" },
  { rank: 12, label: "7 de espadas" },
  { rank: 11, label: "7 de oros" },
  { rank: 10, label: "3" },
  { rank: 9, label: "2" },
  { rank: 8, label: "1 de oros / 1 de copas" },
  { rank: 7, label: "12" },
  { rank: 6, label: "11" },
  { rank: 5, label: "10" },
  { rank: 4, label: "7 de copas / 7 de bastos" },
  { rank: 3, label: "6" },
  { rank: 2, label: "5" },
  { rank: 1, label: "4" },
];

export const ENVIDO_CALL_LABELS: Record<EnvidoCall, string> = {
  envido: "Envido",
  real_envido: "Real envido",
  falta_envido: "Falta envido",
};

export function sameSettings(a: BotSettings, b: BotSettings): boolean {
  return (Object.keys(a) as (keyof BotSettings)[]).every((k) => a[k] === b[k]);
}
