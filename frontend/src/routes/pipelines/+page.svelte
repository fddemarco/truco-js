<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { api, errorMessage, type Pipeline } from "$lib/api/client";

  let pipelines = $state<Pipeline[]>([]);
  let sources = $state<string[]>([]);
  let error = $state<string | null>(null);
  let editingId = $state<number | null>(null);

  const emptyForm = () => ({
    name: "",
    source: sources[0] ?? "",
    dataset: "raw",
    params: "{}",
  });
  let form = $state(emptyForm());

  async function load() {
    const [p, s] = await Promise.all([
      api.GET("/api/pipelines"),
      api.GET("/api/pipelines/sources"),
    ]);
    pipelines = p.data ?? [];
    sources = s.data ?? [];
    if (!form.source) form.source = sources[0] ?? "";
  }

  function resetForm() {
    editingId = null;
    form = emptyForm();
  }

  function edit(p: Pipeline) {
    editingId = p.id;
    form = {
      name: p.name,
      source: p.source,
      dataset: p.dataset,
      params: JSON.stringify(p.params ?? {}, null, 2),
    };
  }

  async function save(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    let params: Record<string, unknown>;
    try {
      params = JSON.parse(form.params || "{}");
    } catch {
      error = "Params must be valid JSON";
      return;
    }
    const body = { name: form.name, source: form.source, dataset: form.dataset, params };
    const res = editingId
      ? await api.PATCH("/api/pipelines/{pipeline_id}", {
          params: { path: { pipeline_id: editingId } },
          body,
        })
      : await api.POST("/api/pipelines", { body });
    if (res.error) {
      error = errorMessage(res.error);
      return;
    }
    resetForm();
    await load();
  }

  async function toggle(p: Pipeline) {
    await api.PATCH("/api/pipelines/{pipeline_id}", {
      params: { path: { pipeline_id: p.id } },
      body: { enabled: !p.enabled },
    });
    await load();
  }

  async function remove(p: Pipeline) {
    if (!confirm(`Delete pipeline "${p.name}" and its run history?`)) return;
    await api.DELETE("/api/pipelines/{pipeline_id}", { params: { path: { pipeline_id: p.id } } });
    await load();
  }

  async function run(p: Pipeline) {
    const res = await api.POST("/api/pipelines/{pipeline_id}/run", {
      params: { path: { pipeline_id: p.id } },
    });
    if (res.error) error = errorMessage(res.error);
    else goto(`/runs?pipeline_id=${p.id}`);
  }

  onMount(load);
</script>

<div class="grid gap-6 lg:grid-cols-3">
  <section class="card lg:col-span-2">
    <h2 class="mb-3 text-lg font-semibold">Pipelines</h2>
    {#if !pipelines.length}
      <p class="text-sm text-slate-500">No pipelines yet. Create one →</p>
    {:else}
      <table class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Source</th>
            <th>Dataset</th>
            <th>Enabled</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each pipelines as p (p.id)}
            <tr>
              <td class="font-medium">{p.name}</td>
              <td><code>{p.source}</code></td>
              <td>{p.dataset}</td>
              <td><input type="checkbox" checked={p.enabled} onchange={() => toggle(p)} /></td>
              <td class="flex justify-end gap-2">
                <button class="btn btn-primary" disabled={!p.enabled} onclick={() => run(p)}>
                  Run
                </button>
                <button class="btn" onclick={() => edit(p)}>Edit</button>
                <button class="btn btn-danger" onclick={() => remove(p)}>Delete</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <section class="card">
    <h2 class="mb-3 text-lg font-semibold">{editingId ? "Edit pipeline" : "New pipeline"}</h2>
    <form class="space-y-3" onsubmit={save}>
      <label class="block text-sm">
        Name
        <input bind:value={form.name} class="input" required />
      </label>
      <label class="block text-sm">
        Source
        <select bind:value={form.source} class="input" required>
          {#each sources as s (s)}
            <option value={s}>{s}</option>
          {/each}
        </select>
      </label>
      <label class="block text-sm">
        Dataset (DuckDB schema)
        <input bind:value={form.dataset} class="input" required />
      </label>
      <label class="block text-sm">
        Params (JSON, passed to the source)
        <textarea bind:value={form.params} class="input font-mono" rows="4"></textarea>
      </label>
      {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
      <div class="flex gap-2">
        <button class="btn btn-primary" type="submit">{editingId ? "Save" : "Create"}</button>
        {#if editingId}
          <button class="btn" type="button" onclick={resetForm}>Cancel</button>
        {/if}
      </div>
    </form>
  </section>
</div>
