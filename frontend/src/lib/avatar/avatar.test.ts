import { describe, expect, it } from "vitest";
import { avatarPortrait, avatarSrc, avatarVariants, characterFor, variantFor } from "./avatar";

describe("avatarSrc", () => {
  it("shows the base image without a seña", () => {
    expect(avatarSrc("tiburon")).toBe("/avatars/tiburon/base.webp");
  });

  it("uses one image per seña", () => {
    expect(avatarSrc("roca", "sena_02")).toBe("/avatars/roca/sena_02.webp");
    expect(avatarSrc("roca", "sena_02", "ojo_derecho")).toBe("/avatars/roca/sena_02.webp");
  });

  it("rejects a spot the gesture is not made on", () => {
    expect(() => variantFor("sena_01", "nariz")).toThrow(/sena_01/);
  });
});

describe("avatarPortrait", () => {
  it("is not one of the table variants", () => {
    expect(avatarPortrait("roca")).toBe("/avatars/roca/portrait.webp");
    expect(avatarVariants("roca")).not.toContain(avatarPortrait("roca"));
  });
});

describe("avatarVariants", () => {
  it("lists the base and the eight señas", () => {
    const srcs = avatarVariants("maniaca");
    expect(srcs).toHaveLength(9);
    expect(new Set(srcs).size).toBe(9);
    expect(srcs).toContain(avatarSrc("maniaca", "sena_12"));
  });
});

describe("characterFor", () => {
  it("gives each of six seats its own character and wraps around", () => {
    const six = [0, 1, 2, 3, 4, 5].map(characterFor);
    expect(new Set(six).size).toBe(6);
    expect(characterFor(6)).toBe(characterFor(0));
  });
});
