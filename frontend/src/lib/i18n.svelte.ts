/**
 * UI language. Game terms (mano, envido, truco, pica-pica...) stay in Spanish in every locale.
 */
export type Locale = "es" | "en";
export const LOCALES: Locale[] = ["es", "en"];

const STORAGE_KEY = "locale";

const es = {
  "nav.rules": "Reglamento",
  "lang.label": "Idioma",
  "rules.title": "Reglamento oficial de juego",
  "rules.intro":
    "Reglamento de Se Pica Truco Series Argentina (TSA), Edición 2026, organizado por temas.",
  "rules.source": "Fuente: sepica.com.ar/reglamento. Última actualización: 4 de noviembre de 2026.",
  "rules.chapters": "Cap.",
  "rules.contents": "Secciones",
  "rules.prev": "Anterior",
  "rules.next": "Siguiente",
  "rules.notFound": "Sección no encontrada.",
};

export type MessageKey = keyof typeof es;

const en: Record<MessageKey, string> = {
  "nav.rules": "Rules",
  "lang.label": "Language",
  "rules.title": "Official rules of play",
  "rules.intro":
    "Rules of Se Pica Truco Series Argentina (TSA), 2026 Edition, organized by topic. Game terms are kept in Spanish.",
  "rules.source":
    "Source: sepica.com.ar/reglamento, last updated 4 November 2026. This translation is unofficial; the Spanish text prevails.",
  "rules.chapters": "Ch.",
  "rules.contents": "Sections",
  "rules.prev": "Previous",
  "rules.next": "Next",
  "rules.notFound": "Section not found.",
};

const messages: Record<Locale, Record<MessageKey, string>> = { es, en };

function isLocale(value: unknown): value is Locale {
  return LOCALES.includes(value as Locale);
}

function storedLocale(): Locale {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (isLocale(value)) return value;
  } catch {
    // Storage unavailable: fall back to the default.
  }
  return "es";
}

export const i18n = $state({ locale: storedLocale() });

export function setLocale(locale: Locale): void {
  i18n.locale = locale;
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    // Not persisted; the choice still applies to this session.
  }
}

export function t(key: MessageKey): string {
  return messages[i18n.locale][key];
}
