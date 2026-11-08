import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { BotConfig, BotPreset, BotSettings } from "$lib/api/client";
import BotConfigurator from "./BotConfigurator.svelte";

const base: BotSettings = {
  card_order: "strongest_first",
  envido_sing: "threshold",
  envido_sing_threshold: 27,
  envido_call: "envido",
  envido_accept: "threshold",
  envido_accept_threshold: 25,
  envido_raise_threshold: null,
  truco_sing: "threshold",
  truco_sing_threshold: 11,
  truco_accept: "threshold",
  truco_accept_threshold: 10,
  truco_raise_threshold: null,
  bluff: 0,
};

const presets: BotPreset[] = [
  { key: "prolijo", name: "Prolijo", settings: base },
  {
    key: "cauteloso",
    name: "Cauteloso",
    settings: {
      ...base,
      card_order: "weakest_first",
      envido_sing: "never",
      envido_accept: "never",
    },
  },
];

const saved: BotConfig[] = [
  {
    id: 7,
    name: "Mi bot",
    settings: { ...base, envido_sing: "always" },
    character: null,
    created_at: "2026-11-07T00:00:00Z",
  },
];

function setup(onSave = vi.fn(async (): Promise<string | null> => null)) {
  const view = render(BotConfigurator, { presets, saved, onSave });
  const field = (name: string) =>
    view.container.querySelector(`[name="${name}"]`) as HTMLInputElement;
  return { ...view, field, onSave };
}

describe("BotConfigurator", () => {
  it("starts with the first preset's settings", () => {
    const { field } = setup();
    expect(field("card_order").value).toBe("strongest_first");
    expect(field("envido_sing_threshold").value).toBe("27");
  });

  it("loads a preset from the general selector", async () => {
    const { field } = setup();
    await fireEvent.change(field("bot"), { target: { value: "preset:cauteloso" } });
    expect(field("card_order").value).toBe("weakest_first");
    expect(field("envido_sing").value).toBe("never");
    // "Never" has no threshold to set.
    expect(field("envido_sing_threshold")).toBeNull();
  });

  it("loads a saved bot", async () => {
    const { field } = setup();
    await fireEvent.change(field("bot"), { target: { value: "saved:7" } });
    expect(field("envido_sing").value).toBe("always");
  });

  it("flags edits made in the advanced settings", async () => {
    const { field } = setup();
    expect(screen.queryByText(/Modificado/)).toBeNull();
    await fireEvent.change(field("card_order"), { target: { value: "random" } });
    expect(screen.getByText(/Modificado/)).toBeTruthy();
  });

  it("saves the edited settings under a new name", async () => {
    const { field, onSave } = setup();
    await fireEvent.change(field("card_order"), { target: { value: "cheapest_winner" } });
    await fireEvent.click(field("envido_raise"));
    await fireEvent.input(field("name"), { target: { value: "  Ahorrador  " } });
    await fireEvent.click(screen.getByRole("button", { name: /Roca/ }));
    expect(onSave).not.toHaveBeenCalled();
    await fireEvent.submit(field("name").form!);
    expect(onSave).toHaveBeenLastCalledWith({
      name: "Ahorrador",
      character: "roca",
      settings: { ...base, card_order: "cheapest_winner", envido_raise_threshold: 30 },
    });
    expect(screen.getByRole("status").textContent).toContain("Bot guardado");
    expect(field("name").value).toBe("");
  });

  it("edits an existing bot in place", async () => {
    const onSave = vi.fn(async (): Promise<string | null> => null);
    const editing = { name: "Mi bot", character: "novato" as const, settings: saved[0].settings };
    const view = render(BotConfigurator, { presets, saved, editing, onSave });
    const field = (name: string) =>
      view.container.querySelector(`[name="${name}"]`) as HTMLInputElement;
    expect(field("bot")).toBeNull(); // no "start from" selector
    expect(field("envido_sing").value).toBe("always");
    expect(field("name").value).toBe("Mi bot");
    await fireEvent.input(field("bluff"), { target: { value: "0.5" } });
    await fireEvent.submit(field("name").form!);
    expect(onSave).toHaveBeenCalledWith({
      name: "Mi bot",
      character: "novato",
      settings: { ...saved[0].settings, bluff: 0.5 },
    });
    expect(field("name").value).toBe("Mi bot");
  });

  it("needs a name to save", async () => {
    const { container } = setup();
    const button = container.querySelector('button[type="submit"]') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("shows the error when saving fails", async () => {
    const { field } = setup(vi.fn(async () => "A bot named 'Prolijo' already exists"));
    await fireEvent.input(field("name"), { target: { value: "Prolijo" } });
    await fireEvent.submit(field("name").form!);
    expect(screen.getByRole("status").textContent).toContain("already exists");
    expect(field("name").value).toBe("Prolijo");
  });
});
