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
     import { api, errorMessage } from "$lib/api/client";
     import { t } from "$lib/i18n.svelte";

     let status = $state<string | null>(null);
     let error = $state<string | null>(null);

     onMount(async () => {
       const res = await api.GET("/api/health");
       if (res.error) error = errorMessage(res.error);
       else status = res.data.status;
     });
   </script>

   <section class="card">
     <h2 class="mb-3 text-lg font-semibold">{t("mypage.title")}</h2>
     {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
     <!-- … -->
   </section>
   ```
   Use runes only (`$state`, `$derived`, `$effect`, `$props`) and `onclick={...}` handlers. With SSR off, don't create `+page.server.ts` files.
3. Add the page to `nav` in `frontend/src/routes/+layout.svelte` with a `MessageKey` label. Put every string in both `es` and `en` in `frontend/src/lib/i18n.svelte.ts`. Game terms stay in Spanish in English copy.
4. Put reusable pieces in `frontend/src/lib/components/`, and colocate a `*.test.ts` that uses `@testing-library/svelte`.
5. Style with Tailwind and the shared `.card`, `.btn`, `.btn-primary`, `.input` and `.table` classes.
6. Run `make lint test`. Then check it in the browser with `make dev` and http://localhost:5173/<name>.
