import { afterEach, describe, expect, it } from "vitest";
import { botToken, forgetBotToken, saveBotToken } from "./botTokens";

describe("bot tokens", () => {
  afterEach(() => localStorage.clear());

  it("keeps each bot's token until it is forgotten", () => {
    saveBotToken(1, "a");
    saveBotToken(2, "b");
    forgetBotToken(1);
    expect([botToken(1), botToken(2)]).toEqual([null, "b"]);
  });

  it("survives a corrupt store", () => {
    localStorage.setItem("bot-tokens", "{not json");
    expect(botToken(1)).toBeNull();
    saveBotToken(1, "a");
    expect(botToken(1)).toBe("a");
  });
});
