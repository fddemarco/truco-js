"""Baraja española de 40 cartas and the truco hierarchy (reglamento 5.1, Anexo A)."""

import random
from dataclasses import dataclass
from enum import StrEnum


class Suit(StrEnum):
    ESPADA = "espada"
    BASTO = "basto"
    ORO = "oro"
    COPA = "copa"


NUMBERS = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)

# Anexo A: higher = stronger. Cards in the same group tie (parda between rivals).
_SPECIAL_RANKS = {
    (1, Suit.ESPADA): 14,
    (1, Suit.BASTO): 13,
    (7, Suit.ESPADA): 12,
    (7, Suit.ORO): 11,
}
_RANKS_BY_NUMBER = {3: 10, 2: 9, 1: 8, 12: 7, 11: 6, 10: 5, 7: 4, 6: 3, 5: 2, 4: 1}


@dataclass(frozen=True)
class Card:
    number: int
    suit: Suit

    def __post_init__(self) -> None:
        if self.number not in NUMBERS:
            raise ValueError(f"invalid card number: {self.number}")
        object.__setattr__(self, "suit", Suit(self.suit))

    @property
    def rank(self) -> int:
        """Truco hierarchy (Anexo A), 14 = 1 de espadas ... 1 = any 4."""
        return _SPECIAL_RANKS.get((self.number, self.suit), _RANKS_BY_NUMBER[self.number])

    @property
    def envido_value(self) -> int:
        """1–7 count their number, figuras (10, 11, 12) count 0 (11.1)."""
        return 0 if self.number >= 10 else self.number

    def __str__(self) -> str:
        return f"{self.number} de {self.suit}s"


def new_deck() -> list[Card]:
    return [Card(n, s) for s in Suit for n in NUMBERS]


def shuffled_deck(rng: random.Random) -> list[Card]:
    deck = new_deck()
    rng.shuffle(deck)
    return deck
