import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import type { ScoringInfo } from "$lib/api/client";
import type { ScoringPrefs } from "$lib/scoring";
import ScoringEditor from "./ScoringEditor.svelte";

const c = (family: "envido" | "truco", chain: string[], quiero: number | null, no: number) => ({
  family,
  chain,
  quiero,
  no_quiero: no,
});
const INFO: ScoringInfo = {
  target: 30,
  min_target: 10,
  max_target: 60,
  max_points: 60,
  chains: [
    c("envido", ["envido"], 2, 1),
    c("envido", ["real_envido"], 3, 1),
    c("envido", ["envido", "real_envido"], 5, 2),
    c("truco", ["truco"], 2, 1),
    c("truco", ["retruco"], 3, 1),
    c("truco", ["truco", "retruco"], 3, 2),
  ],
};

function setup(value: ScoringPrefs = { target: 30, chains: [] }) {
  const onChange = vi.fn();
  render(ScoringEditor, { info: INFO, value, onChange });
  return onChange;
}

describe("ScoringEditor", () => {
  it("changes the partido length", async () => {
    const onChange = setup();
    await fireEvent.click(screen.getByRole("button", { name: "18" }));
    expect(onChange).toHaveBeenLastCalledWith({ target: 18, chains: [] });
    await fireEvent.click(screen.getByRole("button", { name: "Más puntos" }));
    expect(onChange).toHaveBeenLastCalledWith({ target: 31, chains: [] });
  });

  it("builds a chain only within one family", async () => {
    const onChange = setup();
    const truco = screen.getByTestId("family-truco");
    await fireEvent.click(within(truco).getByRole("button", { name: /Definir una cadena/ }));
    const builder = within(truco).getByTestId("builder-truco");
    expect(within(builder).queryByRole("button", { name: /Envido/ })).toBeNull();
    await fireEvent.click(within(builder).getByRole("button", { name: "Truco" }));
    // Only what can follow truco is offered.
    expect(within(builder).getByRole("button", { name: "→ Retruco" })).toBeTruthy();
    await fireEvent.click(within(builder).getByRole("button", { name: "→ Retruco" }));
    await fireEvent.click(within(builder).getByRole("button", { name: "Agregar" }));
    expect(onChange).toHaveBeenLastCalledWith({
      target: 30,
      chains: [{ chain: ["truco", "retruco"], quiero: null, no_quiero: null }],
    });
  });

  it("won't define a chain twice", async () => {
    setup({ target: 30, chains: [{ chain: ["truco"], quiero: 3, no_quiero: null }] });
    const truco = screen.getByTestId("family-truco");
    await fireEvent.click(within(truco).getByRole("button", { name: /Definir una cadena/ }));
    const builder = within(truco).getByTestId("builder-truco");
    await fireEvent.click(within(builder).getByRole("button", { name: "Truco" }));
    expect(within(builder).getByRole("status").textContent).toContain("ya está definida");
    expect(
      (within(builder).getByRole("button", { name: "Agregar" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("shows the defaults as placeholders and sets points", async () => {
    const onChange = setup({
      target: 30,
      chains: [{ chain: ["truco", "retruco"], quiero: null, no_quiero: null }],
    });
    const quiero = screen.getByRole("spinbutton", { name: "Truco → Retruco: quiero" });
    const no = screen.getByRole("spinbutton", { name: "Truco → Retruco: no quiero" });
    expect(quiero.getAttribute("placeholder")).toBe("3");
    expect(no.getAttribute("placeholder")).toBe("2");
    await fireEvent.input(quiero, { target: { value: "5" } });
    expect(onChange).toHaveBeenLastCalledWith({
      target: 30,
      chains: [{ chain: ["truco", "retruco"], quiero: 5, no_quiero: null }],
    });
  });
});
