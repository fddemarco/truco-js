"""Seat characters (the avatars, see `docs/art-prompts.md`) and team names."""

import random
from collections.abc import Sequence
from enum import StrEnum


class Character(StrEnum):
    TIBURON = "tiburon"
    MANIACA = "maniaca"
    ROCA = "roca"
    NOVATO = "novato"
    CALCULADORA = "calculadora"
    FANFARRON = "fanfarron"


# Display names: proper names, the same in every language.
CHARACTER_NAMES = {
    Character.TIBURON: "Tiburón",
    Character.MANIACA: "Maníaca",
    Character.ROCA: "Roca",
    Character.NOVATO: "Novato",
    Character.CALCULADORA: "Calculadora",
    Character.FANFARRON: "Fanfarrón",
}

TEAM_NAMES = (
    "Los Pumas",
    "Las Vizcachas",
    "Los Teros",
    "Los Carpinchos",
    "Las Mulitas",
    "Los Chimangos",
    "Los Horneros",
    "Las Calandrias",
    "Los Yaguaretés",
    "Los Ñandúes",
)


def assign_characters(wanted: Sequence[Character | None]) -> list[Character]:
    """One character per seat, never repeated.

    Wanted characters are kept in seat order (a repeat loses it); the other seats take their
    default (seat i → the i-th character) if free, else the next free one.
    """
    characters = list(Character)
    result: list[Character | None] = [None] * len(wanted)
    taken: set[Character] = set()
    for i, c in enumerate(wanted):
        if c is not None and c not in taken:
            result[i] = c
            taken.add(c)
    for i in range(len(wanted)):
        if result[i] is not None:
            continue
        start = i % len(characters)
        free = next(
            characters[(start + k) % len(characters)]
            for k in range(len(characters))
            if characters[(start + k) % len(characters)] not in taken
        )
        result[i] = free
        taken.add(free)
    return [c for c in result if c is not None]


def draw_team_names(rng: random.Random) -> tuple[str, str]:
    a, b = rng.sample(TEAM_NAMES, 2)
    return a, b
