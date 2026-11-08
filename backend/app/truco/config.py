"""Rule modes, chosen when a tournament or a one-off game starts.

- Strict: a fixed, restricted set of moves for the RL bot and for players who want tight
  rules. Envido is resolved automatically, only the player in turn sings, and señas are a
  probabilistic action.
- Interactive: a simulated real table for multiplayer. Cantos fuera de turno, irregular
  cantos, free envido declarations with reclamos, tapar, showing cards and timed señas.
  The engine acts as referee.

Formats, also chosen at the start and played in either mode:

- Reglamento: three against three, manos redondas alternating with pica-pica (15.1).
- Redonda: three against three, every mano redonda (no pica-pica).
- Pica-pica: one against one, a whole partido as a single duelo: two seats, no partners,
  so no señas and no "nos vamos al mazo"; falta envido is what the leader lacks (11.3), not
  the 6 of a duelo inside a pica-pica mano (15.x).
"""

from dataclasses import dataclass
from enum import StrEnum

from app.truco.scoring import REGLAMENTO, Scoring


class RuleMode(StrEnum):
    STRICT = "strict"
    INTERACTIVE = "interactive"


class Format(StrEnum):
    REGLAMENTO = "reglamento"
    REDONDA = "redonda"
    PICA_PICA = "pica_pica"


@dataclass(frozen=True)
class GameConfig:
    mode: RuleMode = RuleMode.STRICT
    sena_notice_p: float = 0.8  # strict: chance that each teammate notices a seña
    sena_leak_q: float = 0.15  # strict: chance that each rival detects it
    scoring: Scoring = REGLAMENTO  # partido length and canto points (both modes)
    format: Format = Format.REGLAMENTO

    @property
    def players(self) -> int:
        """Seats at the table: 6, or 2 for a pica-pica partido (one against one)."""
        return 2 if self.format == Format.PICA_PICA else 6

    @property
    def partners(self) -> bool:
        """Each player has teammates (señas, nos vamos al mazo); not one against one."""
        return self.players > 2

    @property
    def interactive(self) -> bool:
        return self.mode == RuleMode.INTERACTIVE
