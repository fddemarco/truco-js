<script lang="ts">
  import type { RunStatus } from "$lib/api/client";

  let { status }: { status: RunStatus } = $props();

  const classes: Record<RunStatus, string> = {
    pending: "bg-slate-100 text-slate-700",
    running: "bg-amber-100 text-amber-800",
    success: "bg-emerald-100 text-emerald-800",
    failed: "bg-red-100 text-red-800",
  };
</script>

<span class={["rounded-full px-2 py-0.5 text-xs font-medium", classes[status]]}>{status}</span>
