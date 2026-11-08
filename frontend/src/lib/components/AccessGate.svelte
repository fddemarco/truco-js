<script lang="ts">
  import { setAccess } from "$lib/access.svelte";
  import { api } from "$lib/api/client";
  import { LOGO } from "$lib/cards";
  import { t, type MessageKey } from "$lib/i18n.svelte";
  import { log } from "$lib/log";

  // The app is behind one shared password (ACCESS_PASSWORD on the server): entering it sets
  // a cookie, and the layout shows the app once `access.locked` is false.
  let password = $state("");
  let busy = $state(false);
  let failure = $state<MessageKey | null>(null);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!password || busy) return;
    busy = true;
    failure = null;
    const { data, response } = await api.POST("/api/access", { body: { password } });
    busy = false;
    if (data) {
      log.info("access.granted");
      setAccess(data);
      return;
    }
    failure =
      response.status === 401
        ? "access.wrong"
        : response.status === 429
          ? "access.limited"
          : "access.failed";
    password = "";
  }
</script>

<div class="flex min-h-[70vh] items-center justify-center">
  <form
    class="w-full max-w-sm space-y-5 rounded-2xl bg-white p-6 shadow-2xl"
    aria-labelledby="access-title"
    onsubmit={submit}
  >
    <div class="flex flex-col items-center text-center">
      <img src={LOGO} alt="Truco" width="200" height="72" class="h-14 w-auto" />
      <h1 id="access-title" class="mt-3 text-2xl font-black">{t("access.title")}</h1>
      <p class="text-sm text-slate-600">{t("access.intro")}</p>
    </div>
    <label class="block">
      <span class="text-sm font-semibold">{t("access.password")}</span>
      <!-- svelte-ignore a11y_autofocus -->
      <input
        class="input mt-1 text-lg"
        type="password"
        name="password"
        autocomplete="current-password"
        autofocus
        bind:value={password}
      />
    </label>
    {#if failure}<p class="text-sm text-red-600" role="alert">{t(failure)}</p>{/if}
    <button
      class="btn btn-primary w-full justify-center py-2 text-base"
      disabled={!password || busy}
    >
      {t("access.enter")}
    </button>
  </form>
</div>
