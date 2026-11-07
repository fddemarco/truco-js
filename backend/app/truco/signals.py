"""Señas oficiales (cap. 14, Anexo C).

A seña may be truthful or false (C.1): the engine never checks it against the cards.
- Strict mode: `ActionKind.SENA` is a free action of the player to act. Each teammate notices
  it and each rival detects it with configurable probabilities.
- Interactive mode: a timed `SenaEvent` on a body spot of the signaller's avatar, aimed at a
  teammate. Everyone at the table may see it (14.4); noticing it is up to the players.
"""

from dataclasses import dataclass
from enum import StrEnum


class Sena(StrEnum):
    # Numbered as in C.2. There is no 08, 09, 10 (figures) or 11 (no truco cards): see C.3.
    ANCHO_DE_ESPADAS = "sena_01"  # levantar ambas cejas
    ANCHO_DE_BASTOS = "sena_02"  # guiñar el ojo derecho
    SIETE_DE_ESPADAS = "sena_03"  # comisura de los labios hacia la derecha
    SIETE_DE_OROS = "sena_04"  # comisura de los labios hacia la izquierda
    TRES = "sena_05"  # morder suavemente el labio inferior
    DOS = "sena_06"  # fruncir y proyectar los labios (beso)
    ANCHO_FALSO = "sena_07"  # abrir ligeramente la boca
    BUEN_ENVIDO = "sena_12"  # fruncir la nariz


class BodySpot(StrEnum):
    CEJAS = "cejas"
    OJO_DERECHO = "ojo_derecho"
    COMISURA_DERECHA = "comisura_derecha"
    COMISURA_IZQUIERDA = "comisura_izquierda"
    LABIO_INFERIOR = "labio_inferior"
    LABIOS = "labios"
    BOCA = "boca"
    NARIZ = "nariz"


# Where each gesture can be made. Right and left are from the signaller's view (C.1).
SPOTS: dict[Sena, tuple[BodySpot, ...]] = {
    Sena.ANCHO_DE_ESPADAS: (BodySpot.CEJAS,),
    Sena.ANCHO_DE_BASTOS: (BodySpot.OJO_DERECHO,),
    Sena.SIETE_DE_ESPADAS: (BodySpot.COMISURA_DERECHA,),
    Sena.SIETE_DE_OROS: (BodySpot.COMISURA_IZQUIERDA,),
    Sena.TRES: (BodySpot.LABIO_INFERIOR,),
    Sena.DOS: (BodySpot.LABIOS,),
    Sena.ANCHO_FALSO: (BodySpot.BOCA,),
    Sena.BUEN_ENVIDO: (BodySpot.NARIZ,),
}


@dataclass(frozen=True)
class SenaSeen:
    """Strict mode: a seña that reached an observer."""

    seat: int  # who made it
    sena: Sena
    ronda: int  # 0-based ronda in which it was made


@dataclass(frozen=True)
class SenaEvent:
    """Interactive mode: a seña shown on the signaller's avatar for a while."""

    seat: int
    sena: Sena
    spot: BodySpot
    start_ms: int
    duration_ms: int
    target: int | None = None  # the teammate it is aimed at, if any

    def __post_init__(self) -> None:
        if self.spot not in SPOTS[self.sena]:
            raise ValueError(f"{self.sena} is not made on the {self.spot}")
        if self.duration_ms <= 0:
            raise ValueError("a seña must last some time")
