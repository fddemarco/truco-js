import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    // SPA mode: a static site whose routes all fall back to index.html. /api is FastAPI
    // (the Vite proxy locally, the `backend` Vercel service in production; see vercel.json).
    adapter: adapter({ fallback: "index.html" }),
  },
};
