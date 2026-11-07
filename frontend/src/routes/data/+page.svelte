<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Table, type TablePreview } from "$lib/api/client";
  import { formatCell } from "$lib/format";

  let tables = $state<Table[]>([]);
  let selected = $state<Table | null>(null);
  let preview = $state<TablePreview | null>(null);

  async function loadTables() {
    tables = (await api.GET("/api/data/tables")).data ?? [];
  }

  async function select(t: Table) {
    selected = t;
    const { data } = await api.GET("/api/data/tables/{schema_name}/{table_name}", {
      params: { path: { schema_name: t.schema_name, table_name: t.table_name } },
    });
    preview = data ?? null;
  }

  onMount(loadTables);
</script>

<div class="grid gap-6 lg:grid-cols-4">
  <section class="card">
    <div class="mb-3 flex items-center justify-between">
      <h2 class="text-lg font-semibold">Tables</h2>
      <button class="btn" onclick={loadTables}>↻</button>
    </div>
    {#if !tables.length}
      <p class="text-sm text-slate-500">Run a pipeline to load data.</p>
    {/if}
    <ul class="space-y-1 text-sm">
      {#each tables as t (`${t.schema_name}.${t.table_name}`)}
        <li>
          <button
            class={[
              "w-full rounded px-2 py-1 text-left hover:bg-slate-100",
              selected === t && "bg-indigo-50 font-semibold",
            ]}
            onclick={() => select(t)}
          >
            <span class="text-slate-500">{t.schema_name}.</span>{t.table_name}
            <span class="float-right text-xs text-slate-400">{t.row_count}</span>
          </button>
        </li>
      {/each}
    </ul>
  </section>
  <section class="card overflow-auto lg:col-span-3">
    {#if !preview}
      <p class="text-sm text-slate-500">Select a table to preview.</p>
    {:else}
      <table class="table font-mono text-xs">
        <thead>
          <tr>
            {#each preview.columns as c (c.name)}
              <th>{c.name} <span class="font-normal text-slate-400">{c.type}</span></th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each preview.rows as row, i (i)}
            <tr>
              {#each row as cell, j (j)}
                <td>{formatCell(cell)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
</div>
