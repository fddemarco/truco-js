import { fireEvent, render, screen } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { access, isAccessRefusal } from "$lib/access.svelte";

const POST = vi.fn();
vi.mock("$lib/api/client", () => ({
  api: { POST: (...a: unknown[]) => POST(...a) },
}));

const { default: AccessGate } = await import("./AccessGate.svelte");

async function enter(password: string) {
  await fireEvent.input(screen.getByLabelText("Contraseña"), { target: { value: password } });
  await fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("AccessGate", () => {
  beforeEach(() => {
    POST.mockReset();
    access.checked = true;
    access.locked = true;
  });

  it("unlocks the app with the right password", async () => {
    POST.mockResolvedValue({ data: { required: true, granted: true }, response: { status: 200 } });
    render(AccessGate);
    await enter("pica-pica");
    expect(POST).toHaveBeenCalledWith("/api/access", { body: { password: "pica-pica" } });
    expect(access.locked).toBe(false);
  });

  it("stays locked and says why on a wrong password or too many tries", async () => {
    render(AccessGate);
    POST.mockResolvedValue({ error: { detail: "wrong_password" }, response: { status: 401 } });
    await enter("truco");
    expect((await screen.findByRole("alert")).textContent).toBe("Contraseña incorrecta.");
    POST.mockResolvedValue({ error: { detail: "x" }, response: { status: 429 } });
    await enter("truco");
    expect((await screen.findByRole("alert")).textContent).toMatch(/Demasiados intentos/);
    expect(access.locked).toBe(true);
  });
});

describe("isAccessRefusal", () => {
  it("is the gate's 401 only", () => {
    expect(isAccessRefusal(401, { detail: "access_required" })).toBe(true);
    expect(isAccessRefusal(401, { detail: "wrong_password" })).toBe(false);
    expect(isAccessRefusal(403, { detail: "access_required" })).toBe(false);
    expect(isAccessRefusal(401, null)).toBe(false);
  });
});
