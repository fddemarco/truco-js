import { render, screen } from "@testing-library/svelte";
import { expect, it } from "vitest";
import StatusBadge from "./StatusBadge.svelte";

it("renders the status with its color", () => {
  render(StatusBadge, { props: { status: "failed" } });
  const badge = screen.getByText("failed");
  expect(badge.className).toContain("bg-red-100");
});
