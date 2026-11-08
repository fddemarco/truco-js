"""Configurable scoring: partido length and points per canto chain (1.3–1.5, 11.9, 12.2, Anexo B).

The reglamento plays a partido a 30 with the values of Anexo B and cap. 12. A one-off game may
change them: the target and, per canto chain, the points for quiero and no quiero. A chain is
the sequence of cantos sung in one family, envido or truco: ``(envido, real_envido)`` is not
``(real_envido,)``. Chains never mix families.

Defaults (anything not configured):
- quiero: the reglamento's value. Envido 2, real envido 3, summed along the chain; falta envido
  is what the leader lacks (or 6 in pica-pica). Truco = the level of its last call + 1.
- no quiero: what the chain without its last canto is worth querido (as configured), or 1 for a
  single canto. With nothing configured this is exactly the reglamento (B.3, 12.2).

Applies in both rule modes. Tournaments always use the reglamento (`Scoring()`).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.truco.envido import (
    PICA_PICA_FALTA_ENVIDO,
    VALID_SEQUENCES,
    EnvidoCall,
    reglamento_envido_points,
)
from app.truco.truco import LADDER, TrucoCall

DEFAULT_TARGET = 30
MIN_TARGET = 10
MAX_TARGET = 60
MAX_CHAIN_POINTS = 60
PICA_PICA_FROM = 5  # 15.1
PICA_PICA_MARGIN = 5  # 15.1: pica-pica stops when a team is this close to the target (25 of 30)

Chain = tuple[str, ...]


class ScoringError(ValueError):
    pass


@dataclass(frozen=True)
class ChainPoints:
    quiero: int | None = None  # None: the default
    no_quiero: int | None = None


def chain_family(chain: Sequence[str]) -> str | None:
    """'envido' or 'truco' when `chain` is a chain that can be sung, else None."""
    calls = tuple(chain)
    if not calls:
        return None
    try:
        envido = tuple(EnvidoCall(c) for c in calls)
    except ValueError:
        envido = None
    if envido is not None:
        return "envido" if envido in VALID_SEQUENCES else None
    try:
        levels = [LADDER.index(TrucoCall(c)) for c in calls]
    except ValueError:
        return None
    # A truco chain only climbs (a jump is an irregular canto left unobjected, 12.1, 13.3).
    return "truco" if all(a < b for a, b in zip(levels, levels[1:], strict=False)) else None


def envido_chains() -> list[Chain]:
    return sorted((tuple(map(str, s)) for s in VALID_SEQUENCES), key=lambda c: (len(c), c))


def truco_chains() -> list[Chain]:
    """Every climbing truco chain: the regular ladder prefixes and the jumps."""
    out: list[Chain] = []
    n = len(LADDER)
    for mask in range(1, 1 << n):
        out.append(tuple(str(LADDER[i]) for i in range(n) if mask >> i & 1))
    return sorted(out, key=lambda c: (len(c), [LADDER.index(TrucoCall(x)) for x in c]))


@dataclass(frozen=True)
class Scoring:
    target: int = DEFAULT_TARGET
    chains: Mapping[Chain, ChainPoints] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not MIN_TARGET <= self.target <= MAX_TARGET:
            raise ScoringError(f"the target must be between {MIN_TARGET} and {MAX_TARGET}")
        for chain, points in self.chains.items():
            if chain_family(chain) is None:
                raise ScoringError(f"not a canto chain: {' → '.join(chain) or '(empty)'}")
            for value in (points.quiero, points.no_quiero):
                if value is not None and not 0 <= value <= MAX_CHAIN_POINTS:
                    raise ScoringError(f"points must be between 0 and {MAX_CHAIN_POINTS}")

    @classmethod
    def build(cls, target: int, chains: Sequence[tuple[Sequence[str], ChainPoints]]) -> "Scoring":
        """From a list of definitions; a chain defined twice is an error."""
        out: dict[Chain, ChainPoints] = {}
        for chain, points in chains:
            key = tuple(chain)
            if key in out:
                raise ScoringError(f"chain defined twice: {' → '.join(key)}")
            out[key] = points
        return cls(target, out)

    # --- the scoreboard ------------------------------------------------------------------

    @property
    def malas_max(self) -> int:
        """0–15 malas, 16–30 buenas (1.4), scaled to the target."""
        return self.target // 2

    @property
    def pica_pica_until(self) -> int:
        return self.target - PICA_PICA_MARGIN

    def capped(self, current: int, gained: int) -> int:
        """Anything above the target is discarded (1.5)."""
        return min(self.target, current + gained)

    # --- envido --------------------------------------------------------------------------

    def envido_points(
        self,
        calls: Sequence[EnvidoCall],
        accepted: bool,
        *,
        pica_pica: bool,
        scores: tuple[int, int],
        winner: int,
    ) -> int:
        chain = tuple(map(str, calls))
        if accepted:
            return self._envido_quiero(chain, pica_pica, scores, winner)
        configured = self.chains.get(chain)
        if configured and configured.no_quiero is not None:
            return configured.no_quiero
        # The chain without its last canto, querido (B.3: the sum of what was on the table).
        return self._envido_quiero(chain[:-1], pica_pica, scores, winner) if len(chain) > 1 else 1

    def _envido_quiero(
        self, chain: Chain, pica_pica: bool, scores: tuple[int, int], winner: int
    ) -> int:
        configured = self.chains.get(chain)
        if configured and configured.quiero is not None:
            return configured.quiero
        calls = [EnvidoCall(c) for c in chain]
        if calls[-1] == EnvidoCall.FALTA_ENVIDO:
            if pica_pica:
                return PICA_PICA_FALTA_ENVIDO
            if max(scores) <= self.malas_max:
                return self.target - scores[winner]  # both in malas: it decides the partido
            return self.target - max(scores)
        return reglamento_envido_points(calls)

    # --- truco ---------------------------------------------------------------------------

    def truco_quiero(self, calls: Sequence[TrucoCall]) -> int:
        """Points of the mano with `calls` querido (no calls: 1)."""
        chain = tuple(map(str, calls))
        if not chain:
            return 1
        configured = self.chains.get(chain)
        if configured and configured.quiero is not None:
            return configured.quiero
        return LADDER.index(TrucoCall(chain[-1])) + 2

    def truco_no_quiero(self, calls: Sequence[TrucoCall], accepted: Sequence[TrucoCall]) -> int:
        """Points for the chanters when the last of `calls` is not querido.

        Default: what the calls querido so far (`accepted`) are worth (12.2).
        """
        configured = self.chains.get(tuple(map(str, calls)))
        if configured and configured.no_quiero is not None:
            return configured.no_quiero
        return self.truco_quiero(accepted)


REGLAMENTO = Scoring()
