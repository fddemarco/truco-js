import { describe, expect, it } from "vitest";
import type { ScoringInfo } from "$lib/api/client";
import { defaults, nextCantos, parseScoring, removeChain, scoringSetup, setChain } from "./scoring";

const chain = (family: "envido" | "truco", c: string[], quiero: number | null, no: number) => ({
  family,
  chain: c,
  quiero,
  no_quiero: no,
});
const INFO: ScoringInfo = {
  target: 30,
  chains: [
    chain("envido", ["envido"], 2, 1),
    chain("envido", ["real_envido"], 3, 1),
    chain("envido", ["falta_envido"], null, 1),
    chain("envido", ["envido", "envido"], 4, 2),
    chain("envido", ["envido", "real_envido"], 5, 2),
    chain("envido", ["envido", "falta_envido"], null, 2),
    chain("envido", ["real_envido", "falta_envido"], null, 3),
    chain("truco", ["truco"], 2, 1),
    chain("truco", ["retruco"], 3, 1),
    chain("truco", ["truco", "retruco"], 3, 2),
  ],
};

describe("nextCantos", () => {
  it("offers only cantos that continue a chain of the same family", () => {
    expect(nextCantos(INFO, "envido", [])).toEqual(["envido", "real_envido", "falta_envido"]);
    expect(nextCantos(INFO, "envido", ["real_envido"])).toEqual(["falta_envido"]);
    expect(nextCantos(INFO, "envido", ["falta_envido"])).toEqual([]);
    expect(nextCantos(INFO, "truco", ["truco"])).toEqual(["retruco"]);
  });
});

describe("defaults", () => {
  it("is the reglamento with nothing configured", () => {
    expect(defaults(INFO, [], ["envido", "real_envido"])).toEqual({ quiero: 5, no_quiero: 2 });
    expect(defaults(INFO, [], ["falta_envido"])).toEqual({ quiero: "falta", no_quiero: 1 });
  });

  it("takes no quiero from the configured chain without its last canto", () => {
    const chains = [{ chain: ["truco"], quiero: 4, no_quiero: null }];
    expect(defaults(INFO, chains, ["truco", "retruco"]).no_quiero).toBe(4);
    expect(defaults(INFO, chains, ["retruco"]).no_quiero).toBe(1);
  });
});

describe("setChain", () => {
  it("never defines a chain twice", () => {
    let chains = setChain([], ["truco"], { quiero: 3 });
    chains = setChain(chains, ["truco"], { no_quiero: 2 });
    expect(chains).toEqual([{ chain: ["truco"], quiero: 3, no_quiero: 2 }]);
    expect(removeChain(chains, ["truco"])).toEqual([]);
  });
});

describe("scoringSetup", () => {
  it("is null when everything is the reglamento", () => {
    expect(scoringSetup({ target: 30, chains: [] })).toBeNull();
    expect(
      scoringSetup({ target: 30, chains: [{ chain: ["truco"], quiero: null, no_quiero: null }] }),
    ).toBeNull();
  });

  it("sends the target and the chains with points", () => {
    const prefs = { target: 18, chains: [{ chain: ["truco"], quiero: 3, no_quiero: null }] };
    expect(scoringSetup(prefs)).toEqual(prefs);
  });
});

describe("parseScoring", () => {
  it("drops bad entries, clamps the target and keeps a chain once", () => {
    const parsed = parseScoring({
      target: 500,
      chains: [
        { chain: ["truco"], quiero: 3 },
        { chain: ["truco"], quiero: 9 },
        { chain: ["hack"], quiero: 1 },
        { chain: ["envido"], quiero: -2, no_quiero: 1 },
        "junk",
      ],
    });
    expect(parsed).toEqual({
      target: 60,
      chains: [
        { chain: ["truco"], quiero: 3, no_quiero: null },
        { chain: ["envido"], quiero: null, no_quiero: 1 },
      ],
    });
    expect(parseScoring(null)).toEqual({ target: 30, chains: [] });
  });
});
