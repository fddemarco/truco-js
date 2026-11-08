"""Rule modes, chosen when a tournament or a one-off game starts.

- Strict: a fixed, restricted set of moves for the RL bot and for players who want tight
  rules. Envido is resolved automatically, only the player in turn sings, and señas are a
  probabilistic action.
- Interactive: a simulated real table for multiplayer. Cantos fuera de turno, irregular
  cantos, free envido declarations with reclamos, tapar, showing cards and timed señas.
  The engine acts as referee.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.truco.scoring import REGLAMENTO, Scoring


class RuleMode(StrEnum):
    STRICT = "strict"
    INTERACTIVE = "interactive"


@dataclass(frozen=True)
class GameConfig:
    mode: RuleMode = RuleMode.STRICT
    sena_notice_p: float = 0.8  # strict: chance that each teammate notices a seña
    sena_leak_q: float = 0.15  # strict: chance that each rival detects it
    scoring: Scoring = REGLAMENTO  # partido length and canto points (both modes)

    @property
    def interactive(self) -> bool:
        return self.mode == RuleMode.INTERACTIVE
