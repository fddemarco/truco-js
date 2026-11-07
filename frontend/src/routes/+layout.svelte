<script lang="ts">
  import { page } from "$app/state";
  import "../app.css";

  let { children } = $props();

  const nav = [
    { href: "/pipelines", title: "Pipelines" },
    { href: "/runs", title: "Runs" },
    { href: "/data", title: "Data" },
  ];
</script>

<svelte:head><title>Truco</title></svelte:head>

<div class="min-h-screen">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
      <span class="font-semibold">Truco</span>
      <nav class="flex gap-4 text-sm">
        {#each nav as item (item.href)}
          <a
            href={item.href}
            class={page.url.pathname.startsWith(item.href)
              ? "font-semibold text-indigo-600"
              : "text-slate-600 hover:text-slate-900"}
          >
            {item.title}
          </a>
        {/each}
      </nav>
    </div>
  </header>
  <main class="mx-auto max-w-6xl px-4 py-6">
    {@render children()}
  </main>
</div>
