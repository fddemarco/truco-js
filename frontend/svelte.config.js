import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    // SPA mode: FastAPI is the only server; every route falls back to index.html.
    adapter: adapter({ fallback: "index.html" }),
  },
};
