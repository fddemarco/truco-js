/// <reference types="vitest/config" />
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { defineConfig } from "vite";

// The art's version, appended to its URLs (src/lib/art.ts): a hash of every file in
// static/avatars and static/cards, so new art gets new URLs past the year-long cache.
function artVersion(): string {
  const hash = createHash("sha256");
  for (const dir of ["static/avatars", "static/cards"]) {
    const files = readdirSync(dir, { recursive: true, withFileTypes: true })
      .filter((f) => f.isFile())
      .map((f) => join(f.parentPath, f.name))
      .sort();
    for (const file of files) hash.update(file).update(readFileSync(file));
  }
  return hash.digest("hex").slice(0, 10);
}

export default defineConfig(({ mode }) => ({
  define: { __ART_VERSION__: JSON.stringify(mode === "test" ? "" : artVersion()) },
  plugins: [tailwindcss(), sveltekit(), svelteTesting()],
  server: {
    // `make dev` runs the API on API_PORT; `vercel dev` starts it on a random port and
    // hands it over through the frontend's service binding (vercel.json).
    proxy: {
      "/api": process.env.BACKEND_URL ?? `http://localhost:${process.env.API_PORT ?? 8000}`,
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
    setupFiles: ["src/test-setup.ts"],
  },
}));
