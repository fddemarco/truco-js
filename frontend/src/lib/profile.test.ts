import { describe, expect, it } from "vitest";
import { DEFAULT_PROFILE, parseProfile, profile, updateProfile } from "./profile.svelte";

describe("profile", () => {
  it("falls back to defaults for missing, corrupt or invalid data", () => {
    expect(parseProfile(null)).toEqual(DEFAULT_PROFILE);
    expect(parseProfile("{not json")).toEqual(DEFAULT_PROFILE);
    expect(parseProfile(JSON.stringify({ character: "nadie", musicVolume: 7, name: 3 }))).toEqual({
      ...DEFAULT_PROFILE,
      musicVolume: 1,
    });
  });

  it("keeps valid fields, trimmed", () => {
    const p = parseProfile(JSON.stringify({ name: "  Ana ", character: "roca", muted: true }));
    expect(p).toMatchObject({ name: "Ana", character: "roca", muted: true });
  });

  it("updates and persists", () => {
    updateProfile({ name: "Beto", character: "novato" });
    expect(profile).toMatchObject({ name: "Beto", character: "novato" });
    expect(parseProfile(localStorage.getItem("profile"))).toMatchObject({ name: "Beto" });
  });
});
