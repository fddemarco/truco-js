<script lang="ts">
  import { avatarSvg, LOOKS, type BodySpot, type Look, type Sena } from "$lib/avatar/avatar";

  interface Props {
    /** A `Look` or an index into the seat presets. */
    look: Look | number;
    label: string;
    /** The seña being shown right now; the table clears it after its duration. */
    sena?: Sena;
    spot?: BodySpot;
    class?: string;
  }

  let { look, label, sena, spot, class: className = "" }: Props = $props();

  const resolved = $derived(typeof look === "number" ? LOOKS[look % LOOKS.length] : look);
  // Built from our own code, never from user input: safe to render as HTML.
  const svg = $derived(avatarSvg({ look: resolved, sena, spot }));
</script>

<div role="img" aria-label={label} class="aspect-[6/7] w-20 {className}">
  {@html svg}
</div>
