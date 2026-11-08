/**
 * Music and sound effects with plain <audio> elements. Files live in static/audio/ (imported
 * from ../assets/audio/ by `pnpm import-art`); a missing file just stays silent. Volumes and
 * mute come from the profile. Browsers only allow sound after the user interacts, so the music
 * starts on the first click or key press.
 */
import { profile } from "$lib/profile.svelte";

export type Sfx = "card" | "shuffle" | "cut" | "deal" | "fosforo" | "ronda" | "win" | "click";

const MUSIC = ["/audio/music-1.ogg", "/audio/music-2.ogg"];
const src = (name: Sfx) => `/audio/${name}.ogg`;

/** The sound a move makes, if any. */
export function sfxFor(kind: string): Sfx | null {
  switch (kind) {
    case "jugar":
      return "card";
    case "reparto":
      return "deal";
    case "ronda":
      return "ronda";
    case "resultado":
      return "win";
    default:
      return null;
  }
}

const volume = (level: number) => (profile.muted ? 0 : level);

export function play(name: Sfx): void {
  const v = volume(profile.sfxVolume);
  if (!v || typeof Audio === "undefined") return;
  try {
    const audio = new Audio(src(name));
    audio.volume = v;
    audio.play().catch(() => {}); // missing file or not allowed yet: stay silent
  } catch {
    // no audio support
  }
}

let music: HTMLAudioElement | null = null;
let track = 0;

/** Start the background music (call from a user gesture); it cycles through the tracks. */
export function startMusic(): void {
  if (typeof Audio === "undefined" || music) return;
  music = new Audio(MUSIC[track]);
  music.volume = volume(profile.musicVolume);
  music.addEventListener("ended", nextTrack);
  music.addEventListener("error", () => {
    // Only the first track is required; without it there is no music.
    if (track > 0) nextTrack();
  });
  music.play().catch(() => {});
}

function nextTrack() {
  if (!music) return;
  track = (track + 1) % MUSIC.length;
  music.src = MUSIC[track];
  music.play().catch(() => {});
}

export function stopMusic(): void {
  music?.pause();
  music = null;
}

/** Keep the music volume in step with the profile (call inside an $effect). */
export function syncMusicVolume(): void {
  const v = volume(profile.musicVolume);
  if (music) music.volume = v;
}
