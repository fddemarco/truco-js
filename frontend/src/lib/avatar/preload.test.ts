import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The preload cache lives for the page, so each test loads a fresh copy of the module.
async function fresh() {
  vi.resetModules();
  return import("./preload");
}

describe("avatar preload", () => {
  let created: string[];
  let pending: Map<string, { resolve: () => void; reject: (e: Error) => void }>;

  beforeEach(() => {
    created = [];
    pending = new Map();
    vi.stubGlobal(
      "Image",
      class {
        src = "";
        decode() {
          created.push(this.src);
          return new Promise<void>((resolve, reject) => pending.set(this.src, { resolve, reject }));
        }
      },
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("fetches every image of each seated character once, even when seated twice", async () => {
    const { preloadAvatars } = await fresh();
    preloadAvatars(["roca", "novato", "roca"]);
    preloadAvatars(["roca"]);

    expect(created).toHaveLength(18);
    expect(new Set(created).size).toBe(18);
    expect(created).toContain("/avatars/roca/sena_12.webp");
    expect(created).toContain("/avatars/novato/base.webp");
  });

  it("marks an image ready only once it is decoded", async () => {
    const { isDecoded, loadImage, preloadAvatars } = await fresh();
    preloadAvatars(["roca"]);
    const src = "/avatars/roca/sena_01.webp";
    expect(isDecoded(src)).toBe(false);

    pending.get(src)!.resolve();
    await loadImage(src);
    expect(isDecoded(src)).toBe(true);
  });

  it("rejects a load that fails and never marks it ready", async () => {
    const { isDecoded, loadImage } = await fresh();
    const src = "/avatars/roca/sena_02.webp";
    const load = loadImage(src);
    pending.get(src)!.reject(new Error("404"));

    await expect(load).rejects.toThrow("404");
    expect(isDecoded(src)).toBe(false);
  });
});
