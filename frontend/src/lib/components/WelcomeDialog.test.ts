import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import { profile } from "$lib/profile.svelte";
import WelcomeDialog from "./WelcomeDialog.svelte";

describe("WelcomeDialog", () => {
  it("needs a name, then saves it with the chosen character", async () => {
    render(WelcomeDialog);
    const start = screen.getByRole("button", { name: "Empezar" }) as HTMLButtonElement;
    expect(start.disabled).toBe(true);
    await fireEvent.input(screen.getByRole("textbox"), { target: { value: "  Ana " } });
    await fireEvent.click(screen.getByRole("button", { name: /Fanfarrón/ }));
    await fireEvent.click(start);
    expect(profile).toMatchObject({ name: "Ana", character: "fanfarron" });
  });
});
