import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import HomeMenu from "./HomeMenu.svelte";

describe("HomeMenu", () => {
  it("leads with the two ways to play, and keeps rules and settings as small icons", () => {
    render(HomeMenu);
    expect(screen.getByRole("link", { name: /Jugar en línea/ }).getAttribute("href")).toBe(
      "/play?where=online",
    );
    expect(screen.getByRole("link", { name: /Jugar local/ }).getAttribute("href")).toBe(
      "/play?where=local",
    );
    expect(screen.getByRole("link", { name: "Reglamento" }).getAttribute("href")).toBe("/rules");
    expect(screen.getByRole("link", { name: "Ajustes" }).getAttribute("href")).toBe("/settings");
  });
});
