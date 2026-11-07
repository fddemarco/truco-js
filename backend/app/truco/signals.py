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
    ANCHO_DE_ESPADAS = "sena_01"  # levantar ambas cejas
    ANCHO_DE_BASTOS = "sena_02"  # guiñar el ojo derecho
    SIETE_DE_ESPADAS = "sena_03"  # comisura de los labios hacia la derecha
    SIETE_DE_OROS = "sena_04"  # comisura de los labios hacia la izquierda
    TRES = "sena_05"  # morder suavemente el labio inferior
    DOS = "sena_06"  # fruncir y proyectar los labios (beso)
    ANCHO_FALSO = "sena_07"  # abrir ligeramente la boca
    SOTA = "sena_08"  # tocarse la muñeca
    CABALLO = "sena_09"  # tocarse el codo
    REY = "sena_10"  # tocarse el hombro
    SIN_CARTAS_DE_TRUCO = "sena_11"  # cerrar ambos ojos
    BUEN_ENVIDO = "sena_12"  # fruncir la nariz


class BodySpot(StrEnum):
    CEJAS = "cejas"
    OJO_DERECHO = "ojo_derecho"
    OJOS = "ojos"
    COMISURA_DERECHA = "comisura_derecha"
    COMISURA_IZQUIERDA = "comisura_izquierda"
    LABIO_INFERIOR = "labio_inferior"
    LABIOS = "labios"
    BOCA = "boca"
    NARIZ = "nariz"
    MUNECA_DERECHA = "muneca_derecha"
    MUNECA_IZQUIERDA = "muneca_izquierda"
    CODO_DERECHO = "codo_derecho"
    CODO_IZQUIERDO = "codo_izquierdo"
    HOMBRO_DERECHO = "hombro_derecho"
    HOMBRO_IZQUIERDO = "hombro_izquierdo"


# Where each gesture can be made. Right and left are from the signaller's view (C.1).
SPOTS: dict[Sena, tuple[BodySpot, ...]] = {
    Sena.ANCHO_DE_ESPADAS: (BodySpot.CEJAS,),
    Sena.ANCHO_DE_BASTOS: (BodySpot.OJO_DERECHO,),
    Sena.SIETE_DE_ESPADAS: (BodySpot.COMISURA_DERECHA,),
    Sena.SIETE_DE_OROS: (BodySpot.COMISURA_IZQUIERDA,),
    Sena.TRES: (BodySpot.LABIO_INFERIOR,),
    Sena.DOS: (BodySpot.LABIOS,),
    Sena.ANCHO_FALSO: (BodySpot.BOCA,),
    Sena.SOTA: (BodySpot.MUNECA_DERECHA, BodySpot.MUNECA_IZQUIERDA),
    Sena.CABALLO: (BodySpot.CODO_DERECHO, BodySpot.CODO_IZQUIERDO),
    Sena.REY: (BodySpot.HOMBRO_DERECHO, BodySpot.HOMBRO_IZQUIERDO),
    Sena.SIN_CARTAS_DE_TRUCO: (BodySpot.OJOS,),
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
