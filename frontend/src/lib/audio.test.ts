import { afterEach, describe, expect, it, vi } from "vitest";
import { play, playlistFor, sfxFor } from "./audio.svelte";
import { updateProfile } from "./profile.svelte";

/** The music player is module state: each music test starts from a fresh module. */
async function freshAudio() {
  vi.resetModules();
  return import("./audio.svelte");
}

describe("audio", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    updateProfile({ muted: false, sfxVolume: 0.8 });
  });

  it("gives moves their sound", () => {
    expect(sfxFor("jugar")).toBe("card");
    expect(sfxFor("reparto")).toBeNull();
    expect(sfxFor("quiero")).toBeNull();
  });

  it("plays at the profile's volume, and not at all when muted", () => {
    const made: { src: string; volume: number }[] = [];
    vi.stubGlobal(
      "Audio",
      class {
        volume = 1;
        constructor(public src: string) {
          made.push(this);
        }
        play() {
          return Promise.resolve();
        }
      },
    );
    updateProfile({ sfxVolume: 0.5 });
    play("card");
    expect(made).toEqual([{ src: "/audio/card.ogg", volume: 0.5 }]);
    updateProfile({ muted: true });
    play("card");
    expect(made).toHaveLength(1);
  });

  it("plays the menus', the settings' or the table's music by page", () => {
    expect(playlistFor("/")).toBe("menu");
    expect(playlistFor("/play")).toBe("menu"); // setting up a game
    expect(playlistFor("/rules/teams")).toBe("menu");
    expect(playlistFor("/settings")).toBe("settings");
    expect(playlistFor("/play/abc123")).toBe("game");
  });

  it("switches the playing music when the page changes playlist", async () => {
    const { setPlaylist, startMusic } = await freshAudio();
    const made: { src: string }[] = [];
    vi.stubGlobal(
      "Audio",
      class {
        volume = 1;
        constructor(public src: string) {
          made.push(this);
        }
        play() {
          return Promise.resolve();
        }
        pause() {}
        addEventListener() {}
      },
    );
    setPlaylist("menu");
    startMusic();
    expect(made[0].src).toBe("/audio/menu-1.ogg");
    setPlaylist("game");
    expect(made[0].src).toBe("/audio/music-1.ogg"); // the same player, a new track
    setPlaylist("game");
    expect(made).toHaveLength(1);
  });

  it("keeps trying to start the music until the browser allows it", async () => {
    const { setPlaylist, startMusic } = await freshAudio();
    const made: { src: string }[] = [];
    let allowed = false;
    vi.stubGlobal(
      "Audio",
      class {
        volume = 1;
        constructor(public src: string) {
          made.push(this);
        }
        play() {
          return allowed ? Promise.resolve() : Promise.reject(new Error("NotAllowedError"));
        }
        pause() {}
        addEventListener() {}
      },
    );
    setPlaylist("menu");
    expect(await startMusic()).toBe(false); // on load, before any gesture
    allowed = true;
    expect(await startMusic()).toBe(true); // the next gesture
    expect(made).toHaveLength(1); // the same player both times
  });
});
