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
  "nav.bots": "Bots",
  "bots.title": "Bots",
  "bots.intro":
    "Bots de estrategia local: deciden solo con sus cartas y la mesa, sin señas ni cooperación con sus compañeros. Juegan en modo estricto.",
  "bots.selector": "Bot",
  "bots.presets": "Predefinidos",
  "bots.saved": "Guardados",
  "bots.advanced": "Configuración avanzada",
  "bots.modified": "Modificado: guardalo con un nombre nuevo.",
  "bots.cards": "Cartas",
  "bots.cardOrder": "Orden de juego",
  "bots.cardOrder.strongest_first": "La más fuerte primero, después la segunda y la tercera",
  "bots.cardOrder.weakest_first": "La más débil primero",
  "bots.cardOrder.cheapest_winner": "La más barata que gane la ronda",
  "bots.cardOrder.random": "Al azar",
  "bots.policy.always": "Siempre",
  "bots.policy.never": "Nunca",
  "bots.policy.threshold": "Según umbral",
  "bots.sing": "Cantar",
  "bots.accept": "Querer",
  "bots.threshold": "Umbral",
  "bots.raise": "Subir",
  "bots.raiseWhen": "Subir desde",
  "bots.envidoCall": "Canto de envido",
  "bots.tantoHint": "Tanto (0–33)",
  "bots.rankHint": "Su mejor carta para el truco",
  "bots.bluff": "Faroleo (cantar truco por debajo del umbral)",
  "bots.name": "Nombre del nuevo bot",
  "bots.save": "Guardar bot",
  "bots.savedOk": "Bot guardado.",
  "bots.delete": "Borrar",
  "bots.noSaved": "Todavía no guardaste ningún bot.",
  "bots.preset.prolijo": "Equilibrado: canta envido con 27 o más y truco con un 7 de oros o mejor.",
  "bots.preset.envidioso": "Siempre empieza con envido y siempre lo quiere.",
  "bots.preset.cauteloso": "Nunca canta envido y le dice que no; juega primero la más débil.",
  "bots.preset.mentiroso": "Juega al azar y canta truco de farol la mitad de las veces.",
  "bots.preset.ahorrativo": "Gana cada ronda con la carta más barata posible.",
  "nav.play": "Jugar",
  "play.title": "Nueva partida",
  "play.intro":
    "Seis asientos, dos equipos de tres sentados alternadamente. Los del mismo número se enfrentan.",
  "play.mode": "Modo",
  "play.mode.strict": "Estricto: jugadas limitadas, envido automático, señas con probabilidad",
  "play.mode.interactive":
    "Interactivo: mesa real, cantos fuera de turno, declaraciones, reclamos y señas con el teclado",
  "play.where": "Jugadores humanos",
  "play.local": "En este dispositivo (se pasan la pantalla)",
  "play.online": "En línea: cada uno se une con el enlace",
  "play.seat": "Asiento",
  "play.team": "Equipo",
  "play.number": "número",
  "play.human": "Humano",
  "play.bot": "Bot",
  "play.name": "Nombre",
  "play.create": "Empezar partida",
  "play.needHuman": "Al menos un asiento tiene que ser humano.",
  "game.joinTitle": "Elegí un asiento libre",
  "game.join": "Unirme",
  "game.noSeats": "No quedan asientos libres: mirás como espectador.",
  "game.waiting": "Esperando que se unan todos los jugadores…",
  "game.share": "Compartí este enlace para que se unan:",
  "game.turnOf": "Turno de {name}",
  "game.passDevice": "Pasale el dispositivo a {name}.",
  "game.reveal": "Ver mis cartas",
  "game.mySeats": "Mis asientos",
  "game.spectator": "Espectador",
  "game.team": "Equipo {n}",
  "game.dealer": "Repartidor",
  "game.out": "Fuera",
  "game.next": "Siguiente mano",
  "game.won": "¡Ganó el equipo {n}!",
  "game.noWinner": "Partido sin ganador.",
  "game.moves": "Jugadas",
  "game.declare": "Declarar tanto",
  "game.senaPick": "Hacer una seña…",
  "game.senaHelp": "Mantené 1–9, 0, - o = para hacer una seña; con Shift, del lado izquierdo.",
  "game.senasSeen": "Señas que notaste",
  "game.handNumber": "Mano {n}",
  "game.endMano": "Fin de la mano",
  "game.envidoWon": "ganó el envido",
  "game.interference": "interferencia",
  "game.claimUpheld": "reclamo aceptado",
  "game.claimRejected": "reclamo rechazado",
  "game.deal": "Reparto",
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
  "nav.bots": "Bots",
  "bots.title": "Bots",
  "bots.intro":
    "Local-strategy bots: they decide only from their own cards and the table, with no señas and no teamwork. They play strict mode.",
  "bots.selector": "Bot",
  "bots.presets": "Presets",
  "bots.saved": "Saved",
  "bots.advanced": "Advanced settings",
  "bots.modified": "Modified: save it under a new name.",
  "bots.cards": "Cards",
  "bots.cardOrder": "Play order",
  "bots.cardOrder.strongest_first": "Strongest first, then the second, then the third",
  "bots.cardOrder.weakest_first": "Weakest first",
  "bots.cardOrder.cheapest_winner": "Cheapest card that wins the ronda",
  "bots.cardOrder.random": "Random",
  "bots.policy.always": "Always",
  "bots.policy.never": "Never",
  "bots.policy.threshold": "By threshold",
  "bots.sing": "Sing",
  "bots.accept": "Accept (quiero)",
  "bots.threshold": "Threshold",
  "bots.raise": "Raise",
  "bots.raiseWhen": "Raise from",
  "bots.envidoCall": "Envido call",
  "bots.tantoHint": "Tanto (0–33)",
  "bots.rankHint": "Its best card for the truco",
  "bots.bluff": "Bluff (sing truco below the threshold)",
  "bots.name": "New bot name",
  "bots.save": "Save bot",
  "bots.savedOk": "Bot saved.",
  "bots.delete": "Delete",
  "bots.noSaved": "No saved bots yet.",
  "bots.preset.prolijo":
    "Balanced: sings envido with 27 or more and truco with a 7 de oros or better.",
  "bots.preset.envidioso": "Always starts with envido and always accepts it.",
  "bots.preset.cauteloso": "Never sings envido and says no to it; plays its weakest card first.",
  "bots.preset.mentiroso": "Plays at random and bluffs truco half the time.",
  "bots.preset.ahorrativo": "Wins each ronda with the cheapest card it can.",
  "nav.play": "Play",
  "play.title": "New game",
  "play.intro":
    "Six seats, two teams of three seated alternately. Players with the same number face each other.",
  "play.mode": "Mode",
  "play.mode.strict": "Strict: limited moves, automatic envido, señas by chance",
  "play.mode.interactive":
    "Interactive: real table, cantos fuera de turno, declarations, reclamos and keyboard señas",
  "play.where": "Human players",
  "play.local": "On this device (pass the screen)",
  "play.online": "Online: each player joins with the link",
  "play.seat": "Seat",
  "play.team": "Team",
  "play.number": "number",
  "play.human": "Human",
  "play.bot": "Bot",
  "play.name": "Name",
  "play.create": "Start game",
  "play.needHuman": "At least one seat must be human.",
  "game.joinTitle": "Pick a free seat",
  "game.join": "Join",
  "game.noSeats": "No free seats left: you are watching as a spectator.",
  "game.waiting": "Waiting for every player to join…",
  "game.share": "Share this link so others can join:",
  "game.turnOf": "{name}'s turn",
  "game.passDevice": "Pass the device to {name}.",
  "game.reveal": "Show my cards",
  "game.mySeats": "My seats",
  "game.spectator": "Spectator",
  "game.team": "Team {n}",
  "game.dealer": "Dealer",
  "game.out": "Out",
  "game.next": "Next mano",
  "game.won": "Team {n} wins!",
  "game.noWinner": "The partido has no winner.",
  "game.moves": "Moves",
  "game.declare": "Declare your tanto",
  "game.senaPick": "Make a seña…",
  "game.senaHelp": "Hold 1–9, 0, - or = to make a seña; with Shift, on the left side.",
  "game.senasSeen": "Señas you noticed",
  "game.handNumber": "Mano {n}",
  "game.endMano": "End of the mano",
  "game.envidoWon": "won the envido",
  "game.interference": "interference",
  "game.claimUpheld": "reclamo upheld",
  "game.claimRejected": "reclamo rejected",
  "game.deal": "Deal",
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

/** `t("game.turnOf", { name })` replaces `{name}` in the message. */
export function t(key: MessageKey, params: Record<string, string | number> = {}): string {
  return messages[i18n.locale][key].replace(/\{(\w+)\}/g, (m, name) =>
    name in params ? String(params[name]) : m,
  );
}
