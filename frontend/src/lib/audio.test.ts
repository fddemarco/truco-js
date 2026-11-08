import { afterEach, describe, expect, it, vi } from "vitest";
import { play, sfxFor } from "./audio.svelte";
import { updateProfile } from "./profile.svelte";

describe("audio", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    updateProfile({ muted: false, sfxVolume: 0.8 });
  });

  it("gives moves their sound", () => {
    expect(sfxFor("jugar")).toBe("card");
    expect(sfxFor("reparto")).toBe("deal");
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
});
