<script lang="ts">
  import BotManager from "$lib/components/BotManager.svelte";
  import { t } from "$lib/i18n.svelte";
</script>

<section class="card space-y-4">
  <h1 class="text-xl font-semibold">{t("bots.title")}</h1>
  <BotManager />
</section>
