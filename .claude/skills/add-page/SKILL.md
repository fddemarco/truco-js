---
name: add-page
description: Add a new page/view to the SvelteKit frontend, wired to the typed API client and the nav. Use for any new UI screen.
---

# Add a UI page (SvelteKit SPA, Svelte 5)

1. Make sure the backend endpoint exists and the types are current. Run `make gen-api` if the API changed (see the `add-endpoint` skill).
2. Create `frontend/src/routes/<name>/+page.svelte`:
   ```svelte
   <script lang="ts">
     import { onMount } from "svelte";
     import { api, errorMessage, type Run } from "$lib/api/client";

     let items = $state<Run[]>([]);
     let error = $state<string | null>(null);

     onMount(async () => {
       const res = await api.GET("/api/runs");
       if (res.error) error = errorMessage(res.error);
       else items = res.data;
     });
   </script>

   <section class="card">
     <h2 class="mb-3 text-lg font-semibold">Title</h2>
     {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
     <!-- … -->
   </section>
   ```
   Use runes only (`$state`, `$derived`, `$effect`, `$props`) and `onclick={...}` handlers. With SSR off, don't create `+page.server.ts` files.
3. Add the page to `nav` in `frontend/src/routes/+layout.svelte`.
4. Put reusable pieces in `frontend/src/lib/components/`, and colocate a `*.test.ts` that uses `@testing-library/svelte`.
5. Style with Tailwind and the shared `.card`, `.btn`, `.btn-primary`, `.input` and `.table` classes.
6. Run `make lint test`. Then check it in the browser with `make dev` and http://localhost:5173/<name>.
