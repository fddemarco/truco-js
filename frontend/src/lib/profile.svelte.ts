/**
 * The player on this device: name, character and sound settings, kept in localStorage.
 * Storage can be missing or blocked (private mode): the profile then lives for the session.
 */
import { CHARACTERS, isCharacter, type Character } from "$lib/avatar/avatar";
import { COMMANDS, KEY_PRESETS, resolveBindings, type Bindings, type KeyChoice } from "$lib/keys";

export interface Profile {
  name: string;
  character: Character;
  musicVolume: number;
  sfxVolume: number;
  muted: boolean;
  /** Key bindings: a preset, or "custom" with `customKeys`. */
  keys: KeyChoice;
  customKeys: Partial<Bindings>;
}

const KEY = "profile";
export const DEFAULT_PROFILE: Profile = {
  name: "",
  character: CHARACTERS[0],
  musicVolume: 0.4,
  sfxVolume: 0.8,
  muted: false,
  keys: "mnemonic",
  customKeys: {},
};

const clamp = (n: unknown, fallback: number) =>
  typeof n === "number" && Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : fallback;

/** A profile from untrusted stored data: anything invalid falls back to the default. */
export function parseProfile(raw: string | null): Profile {
  let data: Record<string, unknown> = {};
  try {
    const parsed = raw ? JSON.parse(raw) : {};
    if (parsed && typeof parsed === "object") data = parsed;
  } catch {
    // corrupt: start over
  }
  return {
    name: typeof data.name === "string" ? data.name.trim().slice(0, 40) : "",
    character: isCharacter(data.character) ? data.character : DEFAULT_PROFILE.character,
    musicVolume: clamp(data.musicVolume, DEFAULT_PROFILE.musicVolume),
    sfxVolume: clamp(data.sfxVolume, DEFAULT_PROFILE.sfxVolume),
    muted: typeof data.muted === "boolean" ? data.muted : DEFAULT_PROFILE.muted,
    keys:
      data.keys === "custom" || (KEY_PRESETS as readonly unknown[]).includes(data.keys)
        ? (data.keys as KeyChoice)
        : DEFAULT_PROFILE.keys,
    customKeys: parseKeys(data.customKeys),
  };
}

function parseKeys(raw: unknown): Partial<Bindings> {
  if (!raw || typeof raw !== "object") return {};
  const keys: Partial<Bindings> = {};
  for (const c of COMMANDS) {
    const code = (raw as Record<string, unknown>)[c];
    if (typeof code === "string" && code.length <= 32) keys[c] = code;
  }
  return keys;
}

function load(): Profile {
  try {
    return parseProfile(localStorage.getItem(KEY));
  } catch {
    return { ...DEFAULT_PROFILE };
  }
}

export const profile = $state<Profile>(load());

/** The key bindings in use. */
export function bindings(): Bindings {
  return resolveBindings(profile.keys, profile.customKeys);
}

/** Change some fields and persist them. */
export function updateProfile(changes: Partial<Profile>): void {
  Object.assign(profile, parseProfile(JSON.stringify({ ...profile, ...changes })));
  try {
    localStorage.setItem(KEY, JSON.stringify(profile));
  } catch {
    // not persisted; fine for this session
  }
}
