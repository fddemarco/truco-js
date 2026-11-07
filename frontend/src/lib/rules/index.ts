import { marked } from "marked";
import type { Locale } from "$lib/i18n.svelte";

/**
 * The reglamento (docs/reglamento-truco-sepica.md) split into topic pages.
 * Each page is `./<locale>/<slug>.md`; Spanish is the official text.
 */
export interface RuleSection {
  slug: string;
  title: Record<Locale, string>;
  chapters: string;
}

export const SECTIONS: RuleSection[] = [
  {
    slug: "format",
    title: { es: "Formato y competencia", en: "Format and competition" },
    chapters: "1",
  },
  { slug: "terminology", title: { es: "Terminología", en: "Terminology" }, chapters: "2" },
  {
    slug: "teams",
    title: { es: "Equipos y presentación", en: "Teams and attendance" },
    chapters: "3–4",
  },
  { slug: "dealing", title: { es: "Mazo y reparto", en: "Deck and dealing" }, chapters: "5–6" },
  {
    slug: "play",
    title: { es: "Desarrollo de la mano", en: "Playing a mano" },
    chapters: "7–9 · A",
  },
  {
    slug: "cantos",
    title: { es: "Cantos: envido y truco", en: "Cantos: envido and truco" },
    chapters: "10–13 · B",
  },
  { slug: "pica-pica", title: { es: "Pica-pica", en: "Pica-pica" }, chapters: "15" },
  {
    slug: "senas",
    title: { es: "Comunicación y señas", en: "Communication and señas" },
    chapters: "14 · C",
  },
  {
    slug: "officiating",
    title: { es: "Marcador y arbitraje", en: "Scoring and officiating" },
    chapters: "16–17 · 20",
  },
  {
    slug: "conduct",
    title: { es: "Integridad y sanciones", en: "Integrity and sanctions" },
    chapters: "18–19",
  },
];

const files = import.meta.glob("./*/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export function ruleMarkdown(slug: string, locale: Locale): string | undefined {
  return files[`./${locale}/${slug}.md`];
}

/** Rendered HTML of a section, without its `# title` line (the page shows the title). */
export function ruleHtml(slug: string, locale: Locale): string | undefined {
  const markdown = ruleMarkdown(slug, locale);
  if (markdown === undefined) return undefined;
  return marked.parse(markdown.replace(/^# .*\n/, ""), { async: false });
}
