/**
 * Music and sound effects with plain <audio> elements. Files live in static/audio/ (imported
 * from ../assets/audio/ by `pnpm import-art`); a missing file just stays silent. Volumes and
 * mute come from the profile. Browsers only allow sound after the user interacts, so the music
 * tries to start on load and again on each click or key press until it plays. Each part of the app has its own playlist: the menus,
 * the settings and the table (see `playlistFor`).
 */
import { profile } from "$lib/profile.svelte";

export type Sfx = "card" | "shuffle" | "turn";

export type Playlist = "menu" | "settings" | "game";
const PLAYLISTS: Record<Playlist, string[]> = {
  menu: ["/audio/menu-1.ogg", "/audio/menu-2.ogg", "/audio/menu-3.ogg"],
  settings: ["/audio/settings.ogg"],
  game: ["/audio/music-1.ogg", "/audio/music-2.ogg"],
};

/** The music for a page: the table has its own, the settings theirs, the rest the menus'. */
export function playlistFor(path: string): Playlist {
  if (/^\/play\/[^/]+/.test(path)) return "game";
  if (path.startsWith("/settings")) return "settings";
  return "menu";
}
const src = (name: Sfx) => `/audio/${name}.ogg`;

/** The sound a move makes, if any. */
export function sfxFor(kind: string): Sfx | null {
  switch (kind) {
    case "jugar":
      return "card";
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
let playlist: Playlist = "menu";
let track = 0;
const tracks = () => PLAYLISTS[playlist];

/** Switch to a page's music; the same playlist keeps playing where it was. */
export function setPlaylist(next: Playlist): void {
  if (next === playlist) return;
  playlist = next;
  track = 0;
  if (!music) return; // startMusic picks it up
  music.src = tracks()[0];
  music.play().catch(() => {});
}

/**
 * Start the background music; it cycles through the tracks. Browsers may refuse sound until the
 * user interacts (and some only count certain gestures), so call it on load and again on every
 * gesture until it resolves true.
 */
export async function startMusic(): Promise<boolean> {
  if (typeof Audio === "undefined") return false;
  if (!music) {
    music = new Audio(tracks()[track]);
    music.volume = volume(profile.musicVolume);
    music.addEventListener("ended", nextTrack);
    music.addEventListener("error", () => {
      // Only the first track is required; without it there is no music.
      if (track > 0) nextTrack();
    });
  }
  try {
    await music.play();
    return true;
  } catch {
    return false; // not allowed yet, or no file: the next gesture tries again
  }
}

function nextTrack() {
  if (!music) return;
  track = (track + 1) % tracks().length;
  music.src = tracks()[track];
  music.play().catch(() => {});
}

/** Keep the music volume in step with the profile (call inside an $effect). */
export function syncMusicVolume(): void {
  const v = volume(profile.musicVolume);
  if (music) music.volume = v;
}
