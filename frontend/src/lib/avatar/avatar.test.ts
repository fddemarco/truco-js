import { describe, expect, it } from "vitest";
import { avatarSvg, LOOKS, SENAS, SPOTS } from "./avatar";

const look = LOOKS[0];

function part(svg: string, name: string): Element {
  const doc = new DOMParser().parseFromString(svg, "image/svg+xml");
  const el = doc.querySelector(`[data-part="${name}"]`);
  if (!el) throw new Error(`no ${name}`);
  return el;
}

describe("avatarSvg", () => {
  it("shows a neutral face without a seña", () => {
    const svg = avatarSvg({ look });
    expect(svg).not.toContain('class="sena"');
    expect(part(svg, "ojo-derecho").getAttribute("data-state")).toBe("abierto");
    expect(part(svg, "boca").getAttribute("data-state")).toBe("sonrisa");
  });

  it("winks the signaller's right eye only", () => {
    const svg = avatarSvg({ look, sena: "sena_02" });
    expect(part(svg, "ojo-derecho").getAttribute("data-state")).toBe("cerrado");
    expect(part(svg, "ojo-izquierdo").getAttribute("data-state")).toBe("abierto");
  });

  it("closes both eyes for no truco cards", () => {
    const svg = avatarSvg({ look, sena: "sena_11" });
    expect(part(svg, "ojo-derecho").getAttribute("data-state")).toBe("cerrado");
    expect(part(svg, "ojo-izquierdo").getAttribute("data-state")).toBe("cerrado");
  });

  it("touches the chosen side with the other hand", () => {
    const right = avatarSvg({ look, sena: "sena_08", spot: "muneca_derecha" });
    expect(part(right, "mano-izquierda").getAttribute("data-touch")).toBe("muneca_derecha");
    const left = avatarSvg({ look, sena: "sena_10", spot: "hombro_izquierdo" });
    expect(part(left, "mano-derecha").getAttribute("data-touch")).toBe("hombro_izquierdo");
  });

  it("defaults to the gesture's first spot", () => {
    const svg = avatarSvg({ look, sena: "sena_09" });
    expect(part(svg, "mano-izquierda").getAttribute("data-touch")).toBe("codo_derecho");
  });

  it("rejects a spot the gesture is not made on", () => {
    expect(() => avatarSvg({ look, sena: "sena_01", spot: "nariz" })).toThrow(/sena_01/);
  });

  it("changes something visible for every seña at every spot", () => {
    const neutral = avatarSvg({ look }).replace(/data-sena="[^"]*"/, "");
    for (const sena of SENAS) {
      for (const spot of SPOTS[sena]) {
        const svg = avatarSvg({ look, sena, spot });
        expect(svg).toContain('class="sena"');
        expect(svg.replace(/data-sena="[^"]*"/, "")).not.toBe(neutral);
      }
    }
  });
});
