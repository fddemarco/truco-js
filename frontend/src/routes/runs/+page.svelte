<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { onDestroy, onMount } from "svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { api, type Pipeline, type Run } from "$lib/api/client";
  import { formatDate, formatDuration } from "$lib/format";

  let runs = $state<Run[]>([]);
  let pipelines = $state<Pipeline[]>([]);
  let expanded = $state<number | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;

  const pipelineId = $derived(
    page.url.searchParams.get("pipeline_id")
      ? Number(page.url.searchParams.get("pipeline_id"))
      : undefined,
  );
  const names = $derived(Object.fromEntries(pipelines.map((p) => [p.id, p.name])));

  async function load() {
    clearTimeout(timer);
    const { data } = await api.GET("/api/runs", {
      params: { query: { pipeline_id: pipelineId } },
    });
    runs = data ?? [];
    // Poll while anything is in flight.
    if (runs.some((r) => r.status === "pending" || r.status === "running")) {
      timer = setTimeout(load, 1500);
    }
  }

  function setFilter(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    goto(value ? `?pipeline_id=${value}` : "?", { replaceState: true });
  }

  onMount(async () => {
    pipelines = (await api.GET("/api/pipelines")).data ?? [];
  });
  onDestroy(() => clearTimeout(timer));

  // Reload whenever the filter changes (and on first render).
  $effect(() => {
    void pipelineId;
    load();
  });
</script>

<section class="card">
  <div class="mb-3 flex items-center justify-between">
    <h2 class="text-lg font-semibold">Runs</h2>
    <div class="flex gap-2">
      <select class="input w-48" value={pipelineId ?? ""} onchange={setFilter}>
        <option value="">All pipelines</option>
        {#each pipelines as p (p.id)}
          <option value={p.id}>{p.name}</option>
        {/each}
      </select>
      <button class="btn" onclick={load}>Refresh</button>
    </div>
  </div>
  {#if !runs.length}
    <p class="text-sm text-slate-500">No runs yet.</p>
  {:else}
    <table class="table">
      <thead>
        <tr>
          <th>#</th>
          <th>Pipeline</th>
          <th>Status</th>
          <th>Started</th>
          <th>Duration</th>
          <th>Rows</th>
        </tr>
      </thead>
      <tbody>
        {#each runs as r (r.id)}
          <tr
            class={{ "cursor-pointer hover:bg-slate-50": r.error }}
            onclick={() => (expanded = expanded === r.id ? null : r.id)}
          >
            <td>{r.id}</td>
            <td>{names[r.pipeline_id] ?? r.pipeline_id}</td>
            <td><StatusBadge status={r.status} /></td>
            <td>{formatDate(r.started_at)}</td>
            <td>{formatDuration(r.started_at, r.finished_at)}</td>
            <td>{r.rows_loaded ?? "—"}</td>
          </tr>
          {#if expanded === r.id && r.error}
            <tr>
              <td colspan="6">
                <pre
                  class="max-h-64 overflow-auto rounded bg-red-50 p-2 text-xs text-red-800">{r.error}</pre>
              </td>
            </tr>
          {/if}
        {/each}
      </tbody>
    </table>
  {/if}
</section>
