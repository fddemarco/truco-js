import { fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it } from "vitest";
import { bindings, profile, updateProfile } from "$lib/profile.svelte";
import KeyBindings from "./KeyBindings.svelte";

describe("KeyBindings", () => {
  afterEach(() => updateProfile({ keys: "qwerty", customKeys: {} }));

  it("goes back from custom keys to the preset", async () => {
    updateProfile({ keys: "custom", customKeys: { card1: "KeyJ" } });
    render(KeyBindings);
    await fireEvent.click(screen.getByRole("radio", { name: /Cómoda/ }));
    expect(profile.keys).toBe("qwerty");
    expect(bindings().card1).toBe("KeyS");
    // A preset is read-only: no key buttons to edit.
    expect(screen.queryByRole("button", { name: /Quiero:/ })).toBeNull();
  });

  it("custom starts from the layout in use and rebinds a key on the next press", async () => {
    render(KeyBindings);
    await fireEvent.click(screen.getByRole("radio", { name: /Personalizada/ }));
    expect(profile.keys).toBe("custom");
    expect(bindings().card1).toBe("KeyS"); // nothing changed yet
    await fireEvent.click(screen.getByRole("button", { name: "Quiero: E" }));
    await fireEvent.keyDown(window, { code: "KeyL" });
    expect(bindings().quiero).toBe("KeyL");
    // Taking a key that was in use leaves its old command without one.
    await fireEvent.click(screen.getByRole("button", { name: "No quiero: W" }));
    await fireEvent.keyDown(window, { code: "KeyL" });
    expect(bindings().no_quiero).toBe("KeyL");
    expect(bindings().quiero).toBe("");
    expect(screen.getByRole("button", { name: "Quiero: sin tecla" })).toBeTruthy();
  });

  it("Escape cancels and keeps the key", async () => {
    updateProfile({ keys: "custom", customKeys: {} });
    render(KeyBindings);
    await fireEvent.click(screen.getByRole("button", { name: "Envido: T" }));
    await fireEvent.keyDown(window, { code: "Escape" });
    expect(bindings().envido).toBe("KeyT");
  });
});
