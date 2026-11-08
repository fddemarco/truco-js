/**
 * The tokens of the bots saved from this browser (`X-Bot-Token`): only a bot's creator can
 * change or delete it. Others' bots can still be played and duplicated.
 */

const KEY = "bot-tokens";

function read(): Record<string, string> {
  try {
    const data = JSON.parse(localStorage.getItem(KEY) ?? "{}");
    return data && typeof data === "object" ? data : {};
  } catch {
    return {};
  }
}

function write(tokens: Record<string, string>): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(tokens));
  } catch {
    // Storage unavailable: the bot can't be changed after this page.
  }
}

export function botToken(id: number): string | null {
  return read()[id] ?? null;
}

export function saveBotToken(id: number, token: string): void {
  write({ ...read(), [id]: token });
}

export function forgetBotToken(id: number): void {
  const tokens = read();
  delete tokens[id];
  write(tokens);
}
