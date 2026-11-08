/**
 * Game scoring setup: the partido length and points per canto chain (backend
 * app/truco/scoring.py). A chain is the sequence of cantos sung in one family, envido or truco:
 * "envido, real envido" is not "real envido". The server lists the chains that can be sung
 * (GET /api/games/scoring) with the reglamento's points, which are the defaults: anything not
 * configured plays as the reglamento. Each chain is defined at most once.
 */
import type { ChainInfo, ChainSetup, ScoringInfo } from "$lib/api/client";

export type Family = ChainInfo["family"];
export const FAMILIES: Family[] = ["envido", "truco"];

export interface ScoringPrefs {
  target: number;
  chains: ChainSetup[];
}

export const DEFAULT_TARGET = 30;
export const MIN_TARGET = 10;
export const MAX_TARGET = 60;
export const MAX_POINTS = 60;
export const DEFAULT_SCORING: ScoringPrefs = { target: DEFAULT_TARGET, chains: [] };

/** Spanish in every locale. */
export const CANTO_LABELS: Record<string, string> = {
  envido: "Envido",
  real_envido: "Real envido",
  falta_envido: "Falta envido",
  truco: "Truco",
  retruco: "Retruco",
  vale_cuatro: "Vale cuatro",
};

export const chainKey = (chain: readonly string[]) => chain.join(">");
export const chainLabel = (chain: readonly string[]) =>
  chain.map((c) => CANTO_LABELS[c] ?? c).join(" → ");

/** The cantos that can follow `prefix` in a chain of `family` (only within its hierarchy). */
export function nextCantos(info: ScoringInfo, family: Family, prefix: readonly string[]): string[] {
  const out: string[] = [];
  for (const c of info.chains) {
    if (c.family !== family || c.chain.length <= prefix.length) continue;
    if (prefix.every((x, i) => c.chain[i] === x) && !out.includes(c.chain[prefix.length]))
      out.push(c.chain[prefix.length]);
  }
  return out;
}

export function findChain(info: ScoringInfo, chain: readonly string[]): ChainInfo | undefined {
  const key = chainKey(chain);
  return info.chains.find((c) => chainKey(c.chain) === key);
}

/** Points with nothing configured for this field: "falta" for falta envido querido. */
export function defaults(
  info: ScoringInfo,
  chains: readonly ChainSetup[],
  chain: readonly string[],
): { quiero: number | "falta"; no_quiero: number } {
  const quieroOf = (c: readonly string[]): number | "falta" => {
    const set = chains.find((x) => chainKey(x.chain) === chainKey(c))?.quiero;
    if (set != null) return set;
    return findChain(info, c)?.quiero ?? "falta";
  };
  // No quiero: what the chain without its last canto is worth querido, or 1 for one canto.
  const prefix = chain.length > 1 ? quieroOf(chain.slice(0, -1)) : 1;
  return { quiero: quieroOf(chain), no_quiero: prefix === "falta" ? 1 : prefix };
}

const isPoints = (n: unknown): n is number =>
  typeof n === "number" && Number.isInteger(n) && n >= 0 && n <= MAX_POINTS;

/** Scoring prefs from untrusted stored data: bad entries dropped, a chain kept once. */
export function parseScoring(raw: unknown): ScoringPrefs {
  if (!raw || typeof raw !== "object") return { ...DEFAULT_SCORING, chains: [] };
  const data = raw as Record<string, unknown>;
  const target =
    typeof data.target === "number" && Number.isInteger(data.target)
      ? Math.min(MAX_TARGET, Math.max(MIN_TARGET, data.target))
      : DEFAULT_TARGET;
  const chains: ChainSetup[] = [];
  const seen = new Set<string>();
  for (const item of Array.isArray(data.chains) ? data.chains : []) {
    if (!item || typeof item !== "object") continue;
    const { chain, quiero, no_quiero } = item as Record<string, unknown>;
    if (!Array.isArray(chain) || !chain.length || chain.length > 4) continue;
    if (!chain.every((c) => typeof c === "string" && c in CANTO_LABELS)) continue;
    const key = chainKey(chain);
    if (seen.has(key)) continue;
    seen.add(key);
    chains.push({
      chain: [...chain],
      quiero: isPoints(quiero) ? quiero : null,
      no_quiero: isPoints(no_quiero) ? no_quiero : null,
    });
  }
  return { target, chains };
}

/** Set one chain's points, adding the chain once (never a second definition). */
export function setChain(
  chains: readonly ChainSetup[],
  chain: readonly string[],
  points: Partial<Pick<ChainSetup, "quiero" | "no_quiero">>,
): ChainSetup[] {
  const key = chainKey(chain);
  const old = chains.find((c) => chainKey(c.chain) === key);
  const next = { chain: [...chain], quiero: null, no_quiero: null, ...old, ...points };
  return old ? chains.map((c) => (chainKey(c.chain) === key ? next : c)) : [...chains, next];
}

export const removeChain = (chains: readonly ChainSetup[], chain: readonly string[]) =>
  chains.filter((c) => chainKey(c.chain) !== chainKey(chain));

/** What a new game sends: null when it is all the reglamento. */
export function scoringSetup(prefs: ScoringPrefs) {
  const chains = prefs.chains.filter((c) => c.quiero !== null || c.no_quiero !== null);
  if (prefs.target === DEFAULT_TARGET && !chains.length) return null;
  return { target: prefs.target, chains };
}
