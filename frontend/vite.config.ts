/// <reference types="vitest/config" />
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [tailwindcss(), sveltekit(), svelteTesting()],
  server: {
    proxy: { "/api": `http://localhost:${process.env.API_PORT ?? 8000}` },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
  },
});
